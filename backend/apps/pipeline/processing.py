"""Document claims, validated publication and durable revision drafts."""

import uuid
from datetime import timedelta

from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from apps.classes.models import Lecture
from apps.classes.permissions import membership_for
from apps.review.models import Node, NodeVersion
from apps.storage import s3
from apps.uploads.models import ParsedDocument, ProcessingJob, SourceFile

from . import drafting, prompts
from .client import ProviderError
from .contract import ContractError, to_xml
from .models import ProcessingRun, RevisionDraft

LEASE = timedelta(minutes=15)


class LostClaim(Exception):
    pass


def claim(model, pk):
    token = uuid.uuid4()
    now = timezone.now()
    count = model.objects.filter(pk=pk).filter(
        Q(status__in=["queued", "failed"]) | Q(status="running", lease_until__lt=now)
    ).update(status="running", token=token, lease_until=now + LEASE, error="")
    return token if count else None


def heartbeat(model, pk, token):
    if not model.objects.filter(pk=pk, token=token, status="running").update(lease_until=timezone.now() + LEASE):
        raise LostClaim("A newer worker owns this operation")


def safe_error(exc):
    if isinstance(exc, ProviderError):
        return str(exc)
    if isinstance(exc, ContractError):
        return "invalid_document_contract"
    return "processing_failed"  # Never persist raw provider/storage exceptions or credentials.


def process(parsed_document_id):
    document = ParsedDocument.objects.select_related("source_file__lecture").get(pk=parsed_document_id)
    run, _ = ProcessingRun.objects.get_or_create(document=document)
    token = claim(ProcessingRun, run.pk)
    if token is None:
        return  # Completed or another worker has an active lease.
    source = document.source_file
    job = None
    try:
        if source.lecture.klass_id != source.klass_id:
            raise ContractError("Source class and lecture do not match")
        # Do not replace existing reviewed/demo/partially-created nodes.
        if document.nodes.exists():
            raise ContractError("Document already has nodes; explicit reprocessing is required")
        scoped = drafting.scoped_key(document.markdown_s3_key, source.klass_id)
        manifest = drafting.asset_manifest(document.assets, source.klass_id)
        job = ProcessingJob.objects.create(source_file=source, stage=ProcessingJob.Stage.PROCESS,
                                           status=ProcessingJob.Status.RUNNING, started_at=timezone.now())
        SourceFile.objects.filter(pk=source.pk).update(status=SourceFile.Status.PROCESSING, error="")
        draft, models = drafting.draft_document(
            raw=s3.get_bytes(scoped), manifest=manifest, context=source.lecture.ta_context, load_asset=s3.get_bytes,
            accounting={"klass_id": source.klass_id, "source_file_id": source.pk},
            heartbeat=lambda: heartbeat(ProcessingRun, run.pk, token),
        )
        xml = to_xml(draft, context={
            "document": str(document.pk), "lecture": str(source.lecture_id), "source": source.original_name,
            "prompt_version": prompts.PROCESS_VERSION,
        }, assets=manifest)
        # Attempt-scoped immutable key: a stale worker cannot overwrite the winning snapshot.
        key = s3.class_key(source.klass_id, "pipeline", document.pk, token, "nodes.xml")
        s3.put_bytes(key, xml, "application/xml")
        with transaction.atomic():
            locked = ProcessingRun.objects.select_for_update().get(pk=run.pk)
            if locked.token != token or locked.status != "running":
                raise LostClaim("A newer worker owns this operation")
            # Serialize publication across documents belonging to the same lecture.
            Lecture.objects.select_for_update().get(pk=source.lecture_id)
            if document.nodes.exists():
                raise ContractError("Document already has nodes")
            maximum = Node.objects.filter(lecture_id=source.lecture_id).aggregate(value=Max("order"))["value"]
            offset = 0 if maximum is None else maximum + 1
            for item, model in zip(draft["nodes"], models, strict=True):
                ref = dict(item["source_ref"])
                if ref["asset_id"]:
                    ref["asset_key"] = manifest[ref["asset_id"]]["key"]
                # Initial state only; never transition an existing review node here.
                node = Node.objects.create(
                    klass_id=source.klass_id, lecture_id=source.lecture_id, document=document,
                    kind=item["kind"], order=offset + item["order"], state=Node.State.TA_REVIEW,
                    confidence=item["confidence"], source_ref=ref,
                )
                node.current_version = NodeVersion.objects.create(
                    node=node, number=1, content=item["content"], extra=item["extra"], author_type="ai",
                    model=model, prompt_version=prompts.PROCESS_VERSION,
                )
                node.save(update_fields=["current_version", "updated_at"])
            ParsedDocument.objects.filter(pk=document.pk).update(xml_s3_key=key)
            SourceFile.objects.filter(pk=source.pk).update(status=SourceFile.Status.DONE, error="")
            ProcessingJob.objects.filter(pk=job.pk).update(status="succeeded", finished_at=timezone.now())
            locked.status, locked.lease_until = "succeeded", None
            locked.save(update_fields=["status", "lease_until", "updated_at"])
    except LostClaim:
        if job:
            ProcessingJob.objects.filter(pk=job.pk).update(status="failed", error="superseded_attempt",
                                                          finished_at=timezone.now())
    except Exception as exc:
        with transaction.atomic():
            owned = ProcessingRun.objects.select_for_update().get(pk=run.pk)
            if owned.token == token and owned.status == "running":
                owned.status, owned.error, owned.lease_until = "failed", safe_error(exc), None
                owned.save(update_fields=["status", "error", "lease_until", "updated_at"])
                if job:
                    SourceFile.objects.filter(pk=source.pk).update(status=SourceFile.Status.FAILED, error=owned.error)
            if job:
                ProcessingJob.objects.filter(pk=job.pk).update(status="failed", error=safe_error(exc),
                                                              finished_at=timezone.now())
        raise


def prepare_revision(revision_id):
    revision = RevisionDraft.objects.select_related(
        "node__document__source_file", "node__lecture", "base_version", "requested_by",
    ).get(pk=revision_id)
    token = claim(RevisionDraft, revision.pk)
    if token is None:
        return
    try:
        node = revision.node
        if node.current_version_id != revision.base_version_id or node.state not in {"processing", "revising"}:
            RevisionDraft.objects.filter(pk=revision.pk, token=token).update(status="stale", lease_until=None)
            return
        member = membership_for(revision.requested_by, node.klass_id)
        if member is None or (node.state == "revising" and member.role != "professor"):
            raise ContractError("Revision requester is no longer authorized")
        source = node.document.source_file
        if node.klass_id != source.klass_id or node.lecture_id != source.lecture_id:
            raise ContractError("Node and document ownership do not match")
        manifest = drafting.asset_manifest(node.document.assets, node.klass_id)
        ref = {key: node.source_ref.get(key) for key in ("page", "asset_id", "box")}
        if not ref["asset_id"] and node.source_ref.get("asset_key"):
            matches = [key for key, asset in manifest.items() if asset["key"] == node.source_ref["asset_key"]]
            if len(matches) != 1:
                raise ContractError("Revision asset cannot be resolved unambiguously")
            ref["asset_id"] = matches[0]
        item = {"id": "n1", "order": 0, "kind": node.kind, "confidence": node.confidence or 0,
                "source_ref": ref, "content": revision.base_version.content, "extra": revision.base_version.extra}
        draft, model = drafting.draft_revision(
            node=item, comment=revision.comment, context=node.lecture.ta_context,
            manifest=manifest, load_asset=s3.get_bytes,
            accounting={"klass_id": node.klass_id, "source_file_id": source.pk, "node_id": node.pk},
        )
        with transaction.atomic():
            node = Node.objects.select_for_update().get(pk=node.pk)
            locked = RevisionDraft.objects.select_for_update().get(pk=revision.pk)
            if locked.token != token or locked.status != "running":
                return
            if node.current_version_id != revision.base_version_id or node.state not in {"processing", "revising"}:
                locked.status = "stale"
            else:
                locked.status, locked.content, locked.model = "ready", draft, model
            locked.lease_until = None
            locked.save()
    except Exception as exc:
        RevisionDraft.objects.filter(pk=revision.pk, token=token, status="running").update(
            status="failed", error=safe_error(exc), lease_until=None,
        )
        raise
