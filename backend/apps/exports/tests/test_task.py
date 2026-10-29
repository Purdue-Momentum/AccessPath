from unittest.mock import patch

import pytest

from apps.exports.checks import Issue
from apps.exports.models import Export
from apps.exports.tasks import build_html_export
from apps.review.models import Node, NodeVersion
from apps.uploads.models import SourceFile


def run_export(world) -> Export:
    export = Export.objects.create(klass=world.klass, lecture=world.lecture, created_by=world.prof)
    build_html_export(str(export.id))
    export.refresh_from_db()
    return export


def test_builds_the_page_and_records_versions(world, fake_s3):
    nodes = [world.add_node(), world.add_node("equation", "E = mc^2"),
             world.add_node("image", "A block on a ramp.", source_ref={"asset_key": "classes/x/assets/ramp.png"})]
    export = run_export(world)

    assert export.status == Export.Status.DONE, export.error
    assert export.version_ids == [str(n.current_version_id) for n in nodes]
    key, body = fake_s3.put.call_args.args
    assert key == f"classes/{world.klass.id}/exports/{export.id}/lecture-4-work-and-energy.html"
    assert export.html_s3_key == key
    assert fake_s3.put.call_args.kwargs["content_type"] == "text/html; charset=utf-8"
    page = body.decode("utf-8")
    assert "<math" in page and 'alt="A block on a ramp."' in page
    fake_s3.get.assert_called_once_with("classes/x/assets/ramp.png")


def test_strips_all_node_metadata(world, fake_s3):
    node = world.add_node(confidence=0.37)
    run_export(world)
    page = fake_s3.put.call_args.args[1].decode("utf-8")
    for leaked in [str(node.id), str(node.current_version_id), "0.37", "approved", "data-"]:
        assert leaked not in page


def test_refuses_when_a_node_is_not_approved(world, fake_s3):
    world.add_node()
    world.add_node(state=Node.State.PROF_REVIEW)
    export = run_export(world)
    assert export.status == Export.Status.FAILED
    assert "1 item is not approved yet (Waiting for professor: 1)" in export.error
    fake_s3.put.assert_not_called()


def test_refuses_an_empty_lecture(world, fake_s3):
    export = run_export(world)
    assert export.status == Export.Status.FAILED
    assert "no content" in export.error


def test_refuses_while_a_file_is_still_processing(world, fake_s3):
    world.add_node()
    SourceFile.objects.create(klass=world.klass, lecture=world.lecture, uploaded_by=world.ta,
                              original_name="l5.pdf", extension="pdf", s3_key="k2",
                              status=SourceFile.Status.PROCESSING)
    assert run_export(world).status == Export.Status.FAILED


def test_never_changes_nodes(world, fake_s3):
    node = world.add_node()
    run_export(world)
    node.refresh_from_db()
    assert node.state == Node.State.APPROVED
    assert NodeVersion.objects.filter(node=node).count() == 1


def test_bad_latex_fails_with_a_message_a_person_can_act_on(world, fake_s3):
    world.add_node("equation", r"\SI{9.81}{m/s^2}")
    export = run_export(world)
    assert export.status == Export.Status.FAILED
    assert export.error == r"Item 1 (equation): Unsupported LaTeX command \SI in: \SI{9.81}{m/s^2}"


def test_failed_accessibility_check_stops_the_export(world, fake_s3):
    world.add_node()
    with patch("apps.exports.tasks.check_html", return_value=[Issue("error", "one-h1", "Two h1s.")]):
        export = run_export(world)
    assert export.status == Export.Status.FAILED
    assert "Two h1s." in export.error
    assert export.check_report == [{"level": "error", "rule": "one-h1", "message": "Two h1s."}]
    fake_s3.put.assert_not_called()


def test_warnings_are_saved_on_a_finished_export(world, fake_s3):
    world.add_node("graph", "Force against displacement.")  # no image file, no long description
    export = run_export(world)
    assert export.status == Export.Status.DONE
    assert len(export.check_report) == 2
    assert all(item["level"] == "warning" for item in export.check_report)


def test_running_twice_builds_once(world, fake_s3):
    world.add_node()
    export = run_export(world)
    build_html_export(str(export.id))
    assert fake_s3.put.call_count == 1


def test_a_crash_marks_the_export_failed_and_reraises(world, fake_s3):
    world.add_node()
    fake_s3.put.side_effect = RuntimeError("S3 is down")
    export = Export.objects.create(klass=world.klass, lecture=world.lecture, created_by=world.prof)
    with pytest.raises(RuntimeError):
        build_html_export(str(export.id))
    export.refresh_from_db()
    assert export.status == Export.Status.FAILED
    assert "Something went wrong" in export.error