"""Fixtures for Lane E tests. Builds its own class, lecture and nodes, so it never depends on seed_demo."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from apps.classes import services as class_services
from apps.classes.models import ClassMembership, Lecture
from apps.review.models import Node, NodeVersion
from apps.uploads.models import ParsedDocument, SourceFile

PNG = b"\x89PNG\r\n\x1a\nnot-a-real-image"


@pytest.fixture
def world(make_user):
    prof = make_user("prof@purdue.edu")
    ta = make_user("ta@purdue.edu")
    klass = class_services.create_class(user=prof, name="Dynamics", course_code="ME 27400", term="Fall 2026")
    ClassMembership.objects.create(user=ta, klass=klass, role=ClassMembership.Role.TA, invited_by=prof)
    lecture = Lecture.objects.create(klass=klass, title="Lecture 4. Work and Energy", order=4)
    source = SourceFile.objects.create(klass=klass, lecture=lecture, uploaded_by=ta, original_name="l4.pdf",
                                       extension="pdf", s3_key="k", status=SourceFile.Status.DONE)
    doc = ParsedDocument.objects.create(source_file=source, markdown_s3_key="m")

    def add_node(kind="text", content="Work is force times distance.", *, state=Node.State.APPROVED,
                 extra=None, source_ref=None, confidence=0.9):
        # Test data only. Real code never sets Node.state. It goes through review.state_machine.
        node = Node.objects.create(klass=klass, lecture=lecture, document=doc, kind=kind, state=state,
                                   order=Node.objects.filter(lecture=lecture).count(), confidence=confidence,
                                   source_ref=source_ref or {})
        node.current_version = NodeVersion.objects.create(node=node, number=1, content=content,
                                                          extra=extra or {}, author_type="ai")
        node.save()
        return node

    return SimpleNamespace(prof=prof, ta=ta, klass=klass, lecture=lecture, source=source, add_node=add_node)


@pytest.fixture
def fake_s3():
    """No MinIO needed. put_bytes is recorded, get_bytes returns a tiny fake image."""
    with patch("apps.storage.s3.put_bytes") as put, patch("apps.storage.s3.get_bytes", return_value=PNG) as get:
        yield SimpleNamespace(put=put, get=get)