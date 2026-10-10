import pytest

from apps.classes import services
from apps.classes.models import ClassMembership, Lecture

Role = ClassMembership.Role
PASSWORD = "a-good-password-123"


def _login(api, email):
    res = api.post("/api/v1/auth/login", {"email": email, "password": PASSWORD})
    assert res.status_code == 200


@pytest.fixture
def setup(make_user):
    """A class with a professor, a TA, an outsider, and one lecture."""
    prof = make_user("prof@purdue.edu")
    klass = services.create_class(user=prof, name="Dynamics", course_code="ME 27400")
    ta = make_user("ta@purdue.edu")
    ClassMembership.objects.create(user=ta, klass=klass, role=Role.TA)
    make_user("outsider@purdue.edu")
    lecture = Lecture.objects.create(klass=klass, title="Intro", order=1, ta_context="start")
    return {"klass": klass, "lecture": lecture}


def _detail_url(class_id, lecture_id):
    return f"/api/v1/classes/{class_id}/lectures/{lecture_id}"


# --- GET --------------------------------------------------------------------


@pytest.mark.django_db
def test_professor_get(api, setup):
    _login(api, "prof@purdue.edu")
    res = api.get(_detail_url(setup["klass"].id, setup["lecture"].id))
    assert res.status_code == 200
    assert res.data["title"] == "Intro"


@pytest.mark.django_db
def test_ta_get(api, setup):
    _login(api, "ta@purdue.edu")
    res = api.get(_detail_url(setup["klass"].id, setup["lecture"].id))
    assert res.status_code == 200


@pytest.mark.django_db
def test_nonmember_get_forbidden(api, setup):
    _login(api, "outsider@purdue.edu")
    res = api.get(_detail_url(setup["klass"].id, setup["lecture"].id))
    assert res.status_code == 403


# --- PATCH ------------------------------------------------------------------


@pytest.mark.django_db
def test_professor_patch_title_and_order(api, setup):
    _login(api, "prof@purdue.edu")
    url = _detail_url(setup["klass"].id, setup["lecture"].id)
    res = api.patch(url, {"title": "Renamed", "order": 5}, format="json")
    assert res.status_code == 200
    setup["lecture"].refresh_from_db()
    assert setup["lecture"].title == "Renamed"
    assert setup["lecture"].order == 5


@pytest.mark.django_db
def test_ta_patch_ta_context_only(api, setup):
    _login(api, "ta@purdue.edu")
    url = _detail_url(setup["klass"].id, setup["lecture"].id)
    res = api.patch(url, {"ta_context": "updated context"}, format="json")
    assert res.status_code == 200
    setup["lecture"].refresh_from_db()
    assert setup["lecture"].ta_context == "updated context"


@pytest.mark.django_db
def test_ta_patch_title_forbidden(api, setup):
    _login(api, "ta@purdue.edu")
    url = _detail_url(setup["klass"].id, setup["lecture"].id)
    res = api.patch(url, {"title": "Hacked"}, format="json")
    assert res.status_code == 403
    setup["lecture"].refresh_from_db()
    assert setup["lecture"].title == "Intro"


@pytest.mark.django_db
def test_ta_patch_order_forbidden(api, setup):
    _login(api, "ta@purdue.edu")
    url = _detail_url(setup["klass"].id, setup["lecture"].id)
    res = api.patch(url, {"order": 9}, format="json")
    assert res.status_code == 403
    setup["lecture"].refresh_from_db()
    assert setup["lecture"].order == 1


@pytest.mark.django_db
def test_nonmember_patch_forbidden(api, setup):
    _login(api, "outsider@purdue.edu")
    url = _detail_url(setup["klass"].id, setup["lecture"].id)
    res = api.patch(url, {"ta_context": "x"}, format="json")
    assert res.status_code == 403


# --- DELETE -----------------------------------------------------------------


@pytest.mark.django_db
def test_professor_delete(api, setup):
    _login(api, "prof@purdue.edu")
    res = api.delete(_detail_url(setup["klass"].id, setup["lecture"].id))
    assert res.status_code == 204
    assert not Lecture.objects.filter(id=setup["lecture"].id).exists()


@pytest.mark.django_db
def test_ta_delete_forbidden(api, setup):
    _login(api, "ta@purdue.edu")
    res = api.delete(_detail_url(setup["klass"].id, setup["lecture"].id))
    assert res.status_code == 403
    assert Lecture.objects.filter(id=setup["lecture"].id).exists()


@pytest.mark.django_db
def test_nonmember_delete_forbidden(api, setup):
    _login(api, "outsider@purdue.edu")
    res = api.delete(_detail_url(setup["klass"].id, setup["lecture"].id))
    assert res.status_code == 403
    assert Lecture.objects.filter(id=setup["lecture"].id).exists()


# --- Create tightening ------------------------------------------------------


@pytest.mark.django_db
def test_ta_create_forbidden(api, setup):
    _login(api, "ta@purdue.edu")
    res = api.post(f"/api/v1/classes/{setup['klass'].id}/lectures", {"title": "New", "order": 2})
    assert res.status_code == 403


@pytest.mark.django_db
def test_professor_create_allowed(api, setup):
    _login(api, "prof@purdue.edu")
    res = api.post(f"/api/v1/classes/{setup['klass'].id}/lectures", {"title": "New", "order": 2})
    assert res.status_code == 201


@pytest.mark.django_db
def test_member_can_list(api, setup):
    _login(api, "ta@purdue.edu")
    res = api.get(f"/api/v1/classes/{setup['klass'].id}/lectures")
    assert res.status_code == 200
