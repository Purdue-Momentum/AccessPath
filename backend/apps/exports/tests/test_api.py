from unittest.mock import patch

from apps.classes import services as class_services
from apps.exports.models import Export
from apps.review.models import Node

PASSWORD = "a-good-password-123"


def login(api, email):
    assert api.post("/api/v1/auth/login", {"email": email, "password": PASSWORD}).status_code == 200


def exports_url(world):
    return f"/api/v1/classes/{world.klass.id}/lectures/{world.lecture.id}/exports"


def test_post_queues_the_build_after_commit(api, world, django_capture_on_commit_callbacks):
    world.add_node()
    login(api, "ta@purdue.edu")
    with patch("apps.exports.tasks.build_html_export.delay") as delay, \
            django_capture_on_commit_callbacks(execute=True):
        res = api.post(exports_url(world))
    assert res.status_code == 202
    assert res.data["status"] == "queued"
    delay.assert_called_once_with(res.data["id"])


def test_post_refuses_when_not_everything_is_approved(api, world):
    world.add_node(state=Node.State.TA_REVIEW)
    login(api, "prof@purdue.edu")
    with patch("apps.exports.tasks.build_html_export.delay") as delay:
        res = api.post(exports_url(world))
    assert res.status_code == 409
    assert "not approved yet" in res.data["detail"]
    assert Export.objects.count() == 0
    delay.assert_not_called()


def test_list_and_detail(api, world):
    export = Export.objects.create(klass=world.klass, lecture=world.lecture, created_by=world.prof)
    login(api, "prof@purdue.edu")
    listed = api.get(exports_url(world))
    assert listed.status_code == 200
    assert [e["id"] for e in listed.data] == [str(export.id)]
    detail = api.get(f"/api/v1/classes/{world.klass.id}/exports/{export.id}")
    assert detail.status_code == 200
    assert detail.data["lecture_title"] == "Lecture 4. Work and Energy"


def test_download_only_when_done(api, world):
    export = Export.objects.create(klass=world.klass, lecture=world.lecture, created_by=world.prof)
    url = f"/api/v1/classes/{world.klass.id}/exports/{export.id}/download"
    login(api, "prof@purdue.edu")
    assert api.get(url).status_code == 409

    Export.objects.filter(id=export.id).update(status=Export.Status.DONE, html_s3_key="classes/x/exports/y/l.html")
    with patch("apps.storage.s3.presign_download", return_value="https://minio.local/signed") as presign:
        res = api.get(url)
    assert res.status_code == 200
    assert res.data["url"] == "https://minio.local/signed"
    presign.assert_called_once_with("classes/x/exports/y/l.html", filename="lecture-4-work-and-energy.html")


def test_outsider_gets_403_on_every_export_endpoint(api, world, make_user):
    export = Export.objects.create(klass=world.klass, lecture=world.lecture, created_by=world.prof)
    make_user("outsider@purdue.edu")
    login(api, "outsider@purdue.edu")
    base = f"/api/v1/classes/{world.klass.id}"
    assert api.get(exports_url(world)).status_code == 403
    assert api.post(exports_url(world)).status_code == 403
    assert api.get(f"{base}/exports/{export.id}").status_code == 403
    assert api.get(f"{base}/exports/{export.id}/download").status_code == 403


def test_member_of_another_class_cannot_reach_this_export_through_their_class(api, world, make_user):
    export = Export.objects.create(klass=world.klass, lecture=world.lecture, created_by=world.prof)
    other_prof = make_user("other@purdue.edu")
    other_class = class_services.create_class(user=other_prof, name="Statics")
    login(api, "other@purdue.edu")
    assert api.get(f"/api/v1/classes/{other_class.id}/exports/{export.id}").status_code == 404
    assert api.get(f"/api/v1/classes/{other_class.id}/lectures/{world.lecture.id}/exports").status_code == 404


def test_logged_out_user_is_refused(api, world):
    assert api.get(exports_url(world)).status_code == 403