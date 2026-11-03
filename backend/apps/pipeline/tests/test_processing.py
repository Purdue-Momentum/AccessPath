import copy
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.classes.models import Lecture
from apps.classes.services import create_class
from apps.pipeline import client, drafting, processing, service
from apps.pipeline.contract import ContractError, validate_xml
from apps.pipeline.models import ProcessingRun, RevisionDraft
from apps.pipeline.tasks import process_document, revise_node
from apps.review.models import Node, NodeVersion
from apps.uploads.models import ParsedDocument, SourceFile


@pytest.fixture
def world(make_user, monkeypatch):
    user = make_user()
    klass = create_class(user=user, name="Mechanics")
    lecture = Lecture.objects.create(klass=klass, title="Work", ta_context="Force and displacement")
    prefix = f"classes/{klass.pk}"
    source = SourceFile.objects.create(klass=klass, lecture=lecture, uploaded_by=user, original_name="work.pdf",
                                       extension=".pdf", s3_key=f"{prefix}/input.pdf", status="processing")
    doc = ParsedDocument.objects.create(source_file=source, markdown_s3_key=f"{prefix}/input.md", assets=[{
        "key": f"{prefix}/graph.png", "kind": "image", "page": 1, "box": [0, 0, 10, 20],
    }])
    text = {"id": "n1", "order": 0, "kind": "text", "confidence": 0.9,
            "source_ref": {"page": None, "asset_id": None, "box": None},
            "content": "Work is force times distance.", "extra": {"heading_level": None}}
    graph = {"id": "n1", "order": 0, "kind": "graph", "confidence": 0.8,
             "source_ref": {"page": 1, "asset_id": "a1", "box": [0, 0, 10, 20]},
             "content": "Force versus displacement.", "extra": {"long_description": "Force rises linearly."}}
    def completion(**kwargs):
        item = graph if kwargs["purpose"] == "describe_image" else text
        return client.Completion({"schema_version": "0.1-proposal", "nodes": [copy.deepcopy(item)]}, "test-model")
    provider = Mock(side_effect=completion)
    get = Mock(side_effect=lambda key: b'<!-- Page: 1 -->\nWork = force times distance.'
               if key.endswith('.md') else b'fake-image')
    put = Mock()
    monkeypatch.setattr(client, "complete", provider)
    monkeypatch.setattr(processing.s3, "get_bytes", get)
    monkeypatch.setattr(processing.s3, "put_bytes", put)
    return SimpleNamespace(user=user, klass=klass, lecture=lecture, source=source, doc=doc,
                           provider=provider, get=get, put=put, text=text, graph=graph)


def test_process_publishes_versions_xml_and_export_asset_keys(world):
    process_document(str(world.doc.pk))
    nodes = list(world.doc.nodes.order_by("order"))
    assert [n.kind for n in nodes] == ["text", "graph"]
    assert all(n.state == "ta_review" and n.current_version.number == 1 for n in nodes)
    assert all(n.current_version.model == "test-model" for n in nodes)
    assert nodes[1].source_ref["asset_key"] == world.doc.assets[0]["key"]
    assert nodes[0].source_ref["page"] == 1
    world.doc.refresh_from_db()
    world.source.refresh_from_db()
    assert world.source.status == "done" and world.doc.pipeline_run.status == "succeeded"
    assert world.source.jobs.get(stage="process").status == "succeeded"
    key, xml, mime = world.put.call_args.args
    assert world.doc.xml_s3_key == key and mime == "application/xml"
    validate_xml(xml, assets={"a1": {}})
    from apps.exports.rendering import node_content
    assert node_content(nodes[1]).asset_key == world.doc.assets[0]["key"]


def test_duplicate_delivery_makes_no_calls_or_versions(world):
    process_document(str(world.doc.pk))
    calls = world.provider.call_count
    process_document(str(world.doc.pk))
    assert world.provider.call_count == calls
    assert world.doc.nodes.count() == 2 and NodeVersion.objects.count() == 2


def test_invalid_result_fails_without_partial_nodes(world):
    world.provider.side_effect = client.ProviderError("invalid_structured_output")
    with pytest.raises(client.ProviderError):
        process_document(str(world.doc.pk))
    assert not world.doc.nodes.exists()
    world.source.refresh_from_db()
    assert world.source.status == "failed" and world.source.error == "invalid_structured_output"
    assert world.doc.pipeline_run.status == "failed"


def test_storage_failure_has_no_partial_publication(world):
    world.put.side_effect = RuntimeError("private storage diagnostics")
    with pytest.raises(RuntimeError):
        process_document(str(world.doc.pk))
    assert not world.doc.nodes.exists()
    world.source.refresh_from_db()
    assert world.source.error == "processing_failed"


def test_cross_class_storage_rejected_before_reads(world):
    world.doc.markdown_s3_key = "classes/somebody-else/private.md"
    world.doc.save()
    with pytest.raises(ContractError):
        process_document(str(world.doc.pk))
    world.get.assert_not_called()
    world.provider.assert_not_called()


def test_class_lecture_mismatch_rejected(world):
    other = create_class(user=world.user, name="Other")
    world.source.klass = other
    world.source.save()
    with pytest.raises(ContractError):
        process_document(str(world.doc.pk))
    world.get.assert_not_called()


def test_expired_claim_can_be_recovered(world):
    run = ProcessingRun.objects.create(document=world.doc, status="running",
                                       lease_until=timezone.now()-timedelta(hours=1))
    process_document(str(world.doc.pk))
    run.refresh_from_db()
    assert run.status == "succeeded"


def test_active_claim_does_not_call_provider(world):
    ProcessingRun.objects.create(document=world.doc, status="running",
                                 lease_until=timezone.now()+timedelta(minutes=10))
    processing.process(str(world.doc.pk))
    world.provider.assert_not_called()


def test_stale_worker_cannot_publish(world):
    def steal(*args):
        ProcessingRun.objects.filter(document=world.doc).update(status="failed", token=None)
    world.put.side_effect = steal
    process_document(str(world.doc.pk))
    assert not world.doc.nodes.exists()
    world.doc.refresh_from_db()
    assert not world.doc.xml_s3_key


def test_two_documents_append_lecture_order(world):
    process_document(str(world.doc.pk))
    source2 = SourceFile.objects.create(klass=world.klass, lecture=world.lecture, uploaded_by=world.user,
                                        original_name="second.pdf", extension=".pdf", s3_key="unused")
    doc2 = ParsedDocument.objects.create(source_file=source2, markdown_s3_key=world.doc.markdown_s3_key)
    process_document(str(doc2.pk))
    assert list(Node.objects.order_by("order").values_list("order", flat=True)) == [0, 1, 2]


def revision_node(world):
    process_document(str(world.doc.pk))
    node = world.doc.nodes.get(kind="text")
    Node.objects.filter(pk=node.pk).update(state="revising")  # Simulate D's transition in tests only.
    node.refresh_from_db()
    return node


def test_revision_prepares_only_then_d_applies(world, monkeypatch, django_capture_on_commit_callbacks):
    node = revision_node(world)
    original = node.current_version
    enqueue = Mock()
    monkeypatch.setattr(revise_node, "delay", enqueue)
    with django_capture_on_commit_callbacks(execute=True):
        pk = service.revise(node.pk, "Explain more clearly", requested_by=world.user)
    enqueue.assert_called_once_with(str(pk))
    world.text["source_ref"]["page"] = 1
    revise_node(str(pk))
    assert RevisionDraft.objects.get(pk=pk).status == "ready"
    node.refresh_from_db()
    assert node.state == "revising" and node.current_version_id == original.pk
    with pytest.raises(service.RevisionError):
        service.apply_revision(pk)
    with transaction.atomic():
        Node.objects.filter(pk=node.pk).update(state="ta_review")  # D's future completion hook.
        version = service.apply_revision(pk)
    assert version.number == 2 and version.author_type == "ai"
    original.refresh_from_db()
    assert original.content == "Work is force times distance."
    assert RevisionDraft.objects.get(pk=pk).status == "applied"


def test_revision_rejects_nonmember(world, make_user):
    node = revision_node(world)
    with pytest.raises(PermissionDenied):
        service.revise(node.pk, "Change it", requested_by=make_user("outsider@example.edu"))


def test_revision_duplicate_request_reuses_draft(world):
    node = revision_node(world)
    first = service.revise(node.pk, "Clearer", requested_by=world.user)
    assert service.revise(node.pk, "Clearer", requested_by=world.user) == first
    with pytest.raises(service.RevisionError):
        service.revise(node.pk, "Different", requested_by=world.user)


def test_revision_stale_input_does_not_overwrite_human_edit(world):
    node = revision_node(world)
    pk = service.revise(node.pk, "Clearer", requested_by=world.user)
    human = NodeVersion.objects.create(node=node, number=2, content="Human correction", author_type="person")
    Node.objects.filter(pk=node.pk).update(current_version=human)
    before = world.provider.call_count
    revise_node(str(pk))
    assert RevisionDraft.objects.get(pk=pk).status == "stale"
    assert world.provider.call_count == before


def test_utf16_and_bounded_chunks():
    raw = '<!-- Slide number: 2 -->\nEquation and text'.encode('utf-16')
    assert drafting.chunks(raw) == [(2, '\nEquation and text')]
    assert all(len(text) <= drafting.CHUNK_CHARS for _, text in drafting.chunks(b'x' * 20_000))
    with pytest.raises(ContractError):
        drafting.chunks(b'x' * (drafting.MAX_MARKDOWN_BYTES + 1))


def test_manifest_rejects_unsupported_media_and_unsafe_keys():
    for asset in ({"key": "classes/c/x.png", "kind": "audio"}, {"key": "classes/c/../x.png"}):
        with pytest.raises(ContractError):
            drafting.asset_manifest([asset], "c")


def test_existing_nodes_are_not_replaced_or_source_marked_failed(world):
    Node.objects.create(klass=world.klass, lecture=world.lecture, document=world.doc,
                        kind="text", order=0, state="approved")
    before = world.source.status
    with pytest.raises(ContractError):
        process_document(str(world.doc.pk))
    assert world.doc.nodes.get().state == "approved"
    world.source.refresh_from_db()
    assert world.source.status == before
    world.provider.assert_not_called()


def test_failed_run_can_be_retried_without_duplicate_nodes(world):
    original = world.provider.side_effect
    world.provider.side_effect = client.ProviderError("http_429")
    with pytest.raises(client.ProviderError):
        process_document(str(world.doc.pk))
    world.provider.side_effect = original
    process_document(str(world.doc.pk))
    assert world.doc.nodes.count() == 2
    assert world.doc.pipeline_run.status == "succeeded"
    assert set(world.source.jobs.values_list("status", flat=True)) == {"failed", "succeeded"}


def test_late_revision_response_is_discarded(world):
    node = revision_node(world)
    pk = service.revise(node.pk, "Clearer", requested_by=world.user)
    world.text["source_ref"]["page"] = 1
    original = world.provider.side_effect
    def edit_during_generation(**kwargs):
        human = NodeVersion.objects.create(node=node, number=2, content="Newer human edit", author_type="person")
        Node.objects.filter(pk=node.pk).update(current_version=human)
        return original(**kwargs)
    world.provider.side_effect = edit_during_generation
    revise_node(str(pk))
    assert RevisionDraft.objects.get(pk=pk).status == "stale"
    node.refresh_from_db()
    assert node.current_version.content == "Newer human edit"


def test_failed_apply_rolls_back_d_transition(world):
    node = revision_node(world)
    pk = service.revise(node.pk, "Clearer", requested_by=world.user)
    world.text["source_ref"]["page"] = 1
    revise_node(str(pk))
    human = NodeVersion.objects.create(node=node, number=2, content="Newer human edit", author_type="person")
    Node.objects.filter(pk=node.pk).update(current_version=human)
    with pytest.raises(service.RevisionError), transaction.atomic():
        Node.objects.filter(pk=node.pk).update(state="ta_review")
        service.apply_revision(pk)
    node.refresh_from_db()
    assert node.state == "revising" and node.versions.count() == 2


def test_missing_asset_and_invalid_confidence_cannot_publish(world):
    world.graph["source_ref"]["asset_id"] = "invented"
    with pytest.raises(ContractError):
        process_document(str(world.doc.pk))
    assert not world.doc.nodes.exists()
    world.put.assert_not_called()


def test_empty_document_fails_explicitly(world):
    world.doc.assets = []
    world.doc.save()
    world.get.side_effect = None
    world.get.return_value = b''
    with pytest.raises(ContractError):
        process_document(str(world.doc.pk))
    world.provider.assert_not_called()
    assert not world.doc.nodes.exists()


def test_revoked_requester_is_rejected_before_model_call(world):
    node = revision_node(world)
    pk = service.revise(node.pk, "Clearer", requested_by=world.user)
    world.klass.memberships.update(status="removed")
    count = world.provider.call_count
    with pytest.raises(ContractError):
        revise_node(str(pk))
    assert world.provider.call_count == count
    assert RevisionDraft.objects.get(pk=pk).status == "failed"


def test_revision_status_requires_membership(world, make_user):
    node = revision_node(world)
    pk = service.revise(node.pk, "Clearer", requested_by=world.user)
    assert service.revision_status(pk, requested_by=world.user)["status"] == "queued"
    with pytest.raises(PermissionDenied):
        service.revision_status(pk, requested_by=make_user("outsider@example.edu"))


def test_revision_records_do_not_block_intentional_class_deletion(world):
    node = revision_node(world)
    service.revise(node.pk, "Clearer", requested_by=world.user)
    world.klass.delete()
    assert not RevisionDraft.objects.exists()


def test_smoke_requires_explicit_live_flag(world, monkeypatch):
    from django.core.management import call_command
    from django.core.management.base import CommandError
    request = Mock()
    monkeypatch.setattr(client, "_request", request)
    with pytest.raises(CommandError, match="run-live"):
        call_command("genai_smoke", class_id=str(world.klass.pk))
    request.assert_not_called()
