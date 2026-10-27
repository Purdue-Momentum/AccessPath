from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from apps.review.models import Node


def test_preview_refuses_a_lecture_that_is_not_approved(world, tmp_path):
    world.add_node(state=Node.State.TA_REVIEW)
    with pytest.raises(CommandError, match="Not ready to export"):
        call_command("export_preview", str(world.lecture.id), out=str(tmp_path / "p.html"))


def test_preview_draft_writes_a_local_file_and_uploads_nothing(world, tmp_path, fake_s3):
    world.add_node(state=Node.State.TA_REVIEW)
    out = tmp_path / "p.html"
    call_command("export_preview", str(world.lecture.id), out=str(out), draft=True, stdout=StringIO())
    assert "<h1>Lecture 4. Work and Energy</h1>" in out.read_text(encoding="utf-8")
    fake_s3.put.assert_not_called()