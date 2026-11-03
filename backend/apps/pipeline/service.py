"""C's public revision API. D still owns review transitions and endpoint wiring."""

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Max

from apps.classes.permissions import membership_for
from apps.review.models import Node, NodeVersion

from . import prompts
from .models import RevisionDraft


class RevisionError(ValueError):
    pass


def revise(node_id, comment: str, *, requested_by):
    """Queue a draft after D's authorized send-back/regenerate transition. Return its UUID.

    The worker prepares a draft only. D must later complete the state transition and
    invoke apply_revision in the SAME transaction; this function never changes Node.state.
    """
    from .tasks import revise_node

    with transaction.atomic():
        node = Node.objects.select_for_update().get(pk=node_id)
        member = membership_for(requested_by, node.klass_id)
        if member is None or (node.state == Node.State.REVISING and member.role != "professor"):
            raise PermissionDenied("Not authorized to revise this node")
        if node.state not in {Node.State.PROCESSING, Node.State.REVISING} or not node.current_version_id:
            raise RevisionError("D must request processing/revision of an existing version first")
        if not isinstance(comment, str) or (node.state == Node.State.REVISING and not comment.strip()):
            raise RevisionError("Send-back requires a comment")
        pending = node.ai_revision_drafts.filter(status__in=["queued", "running", "ready"]).first()
        if pending and pending.base_version_id != node.current_version_id:
            pending.status = "stale"
            pending.save(update_fields=["status", "updated_at"])
            pending = None
        if pending:
            if pending.comment == comment.strip():
                return pending.pk
            raise RevisionError("A different revision is already pending")
        revision = RevisionDraft.objects.create(
            node=node, base_version_id=node.current_version_id, requested_by=requested_by, comment=comment.strip(),
        )
        transaction.on_commit(lambda: revise_node.delay(str(revision.pk)))
        return revision.pk


def apply_revision(revision_id):
    """D-only integration hook: caller must transition to TA review in this transaction.

    No endpoint is wired to this yet. No current version is overwritten if it changed
    while inference ran. The AI version and pointer are written atomically with D's
    transition when called as documented. Callers must not catch errors inside that transaction.
    """
    if not transaction.get_connection().in_atomic_block:
        raise RevisionError("Apply inside the same transaction as D's completion transition")
    revision = RevisionDraft.objects.get(pk=revision_id)
    node = Node.objects.select_for_update().get(pk=revision.node_id)
    revision = RevisionDraft.objects.select_for_update().get(pk=revision_id)
    if revision.status != "ready" or node.current_version_id != revision.base_version_id:
        raise RevisionError("Draft is not ready or was based on an older version")
    if node.state != Node.State.TA_REVIEW:
        raise RevisionError("D must complete the transition to TA review in this transaction")
    maximum = node.versions.aggregate(value=Max("number"))["value"] or 0
    version = NodeVersion.objects.create(
        node=node, number=maximum + 1, content=revision.content["content"], extra=revision.content["extra"],
        author_type="ai", model=revision.model, prompt_version=prompts.REVISION_VERSION, note=revision.comment,
    )
    node.current_version = version
    node.confidence = revision.content["confidence"]
    node.save(update_fields=["current_version", "confidence", "updated_at"])
    revision.status = "applied"
    revision.save(update_fields=["status", "updated_at"])
    return version


def revision_status(revision_id, *, requested_by):
    """Authorized read interface for D's eventual polling endpoint."""
    revision = RevisionDraft.objects.select_related("node").get(pk=revision_id)
    if membership_for(requested_by, revision.node.klass_id) is None:
        raise PermissionDenied("Not authorized to read this revision")
    return {"id": str(revision.pk), "node_id": str(revision.node_id),
            "base_version_id": str(revision.base_version_id), "status": revision.status,
            "error": revision.error, "draft": revision.content if revision.status == "ready" else None}
