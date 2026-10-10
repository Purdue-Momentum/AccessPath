"""Cross-class isolation: a member of class A must never reach class B's data
through class A's URL, and must never act on class B at all without membership."""

import pytest

from apps.classes import services
from apps.classes.models import ClassMembership, Lecture

Role = ClassMembership.Role
PASSWORD = "a-good-password-123"


def _login(api, email):
    res = api.post("/api/v1/auth/login", {"email": email, "password": PASSWORD})
    assert res.status_code == 200


@pytest.fixture
def two_classes(make_user):
    """Class A (actor is professor) and a wholly separate class B."""
    prof_a = make_user("profa@purdue.edu")
    class_a = services.create_class(user=prof_a, name="Class A")

    prof_b = make_user("profb@purdue.edu")
    class_b = services.create_class(user=prof_b, name="Class B")
    member_b = make_user("memberb@purdue.edu")
    membership_b = ClassMembership.objects.create(user=member_b, klass=class_b, role=Role.TA)
    lecture_b = Lecture.objects.create(klass=class_b, title="B lecture", order=1)

    return {
        "class_a": class_a,
        "class_b": class_b,
        "membership_b": membership_b,
        "lecture_b": lecture_b,
    }


# --- Class-A actor addressing class B resources through class A's URL -------


@pytest.mark.django_db
def test_member_detail_patch_cross_class_404(api, two_classes):
    _login(api, "profa@purdue.edu")
    url = f"/api/v1/classes/{two_classes['class_a'].id}/members/{two_classes['membership_b'].id}"
    res = api.patch(url, {"role": "professor"}, format="json")
    assert res.status_code == 404
    two_classes["membership_b"].refresh_from_db()
    assert two_classes["membership_b"].role == Role.TA


@pytest.mark.django_db
def test_member_detail_delete_cross_class_404(api, two_classes):
    _login(api, "profa@purdue.edu")
    url = f"/api/v1/classes/{two_classes['class_a'].id}/members/{two_classes['membership_b'].id}"
    res = api.delete(url)
    assert res.status_code == 404
    two_classes["membership_b"].refresh_from_db()
    assert two_classes["membership_b"].status == ClassMembership.Status.ACTIVE


@pytest.mark.django_db
def test_lecture_detail_get_cross_class_404(api, two_classes):
    _login(api, "profa@purdue.edu")
    url = f"/api/v1/classes/{two_classes['class_a'].id}/lectures/{two_classes['lecture_b'].id}"
    assert api.get(url).status_code == 404


@pytest.mark.django_db
def test_lecture_detail_patch_cross_class_404(api, two_classes):
    _login(api, "profa@purdue.edu")
    url = f"/api/v1/classes/{two_classes['class_a'].id}/lectures/{two_classes['lecture_b'].id}"
    res = api.patch(url, {"title": "hijacked"}, format="json")
    assert res.status_code == 404
    two_classes["lecture_b"].refresh_from_db()
    assert two_classes["lecture_b"].title == "B lecture"


@pytest.mark.django_db
def test_lecture_detail_delete_cross_class_404(api, two_classes):
    _login(api, "profa@purdue.edu")
    url = f"/api/v1/classes/{two_classes['class_a'].id}/lectures/{two_classes['lecture_b'].id}"
    assert api.delete(url).status_code == 404
    assert Lecture.objects.filter(id=two_classes["lecture_b"].id).exists()


# --- Class-A actor hitting class B's own URL while not a member of B --------


@pytest.mark.django_db
def test_members_list_of_other_class_forbidden(api, two_classes):
    _login(api, "profa@purdue.edu")
    assert api.get(f"/api/v1/classes/{two_classes['class_b'].id}/members").status_code == 403


@pytest.mark.django_db
def test_lectures_list_of_other_class_forbidden(api, two_classes):
    _login(api, "profa@purdue.edu")
    assert api.get(f"/api/v1/classes/{two_classes['class_b'].id}/lectures").status_code == 403


@pytest.mark.django_db
def test_invite_create_on_other_class_forbidden(api, two_classes):
    _login(api, "profa@purdue.edu")
    url = f"/api/v1/classes/{two_classes['class_b'].id}/invites"
    assert api.post(url, {"email": "x@purdue.edu", "role": "ta"}).status_code == 403


# --- Invite-acceptance isolation --------------------------------------------


@pytest.mark.django_db
def test_accept_lands_on_invite_class_only(api, two_classes):
    """A token minted for class B can only ever create membership in class B."""
    prof_b = ClassMembership.objects.get(klass=two_classes["class_b"], role=Role.PROFESSOR).user
    _, raw_token = services.create_invite(
        klass=two_classes["class_b"], email="joiner@purdue.edu", role=Role.TA, invited_by=prof_b
    )
    from django.contrib.auth import get_user_model

    get_user_model().objects.create_user(email="joiner@purdue.edu", password=PASSWORD)
    _login(api, "joiner@purdue.edu")
    res = api.post(f"/api/v1/invites/{raw_token}/accept")
    assert res.status_code in (200, 201)

    # Membership lands on class B (invite.klass), never on class A.
    assert ClassMembership.objects.filter(
        user__email="joiner@purdue.edu", klass=two_classes["class_b"]
    ).exists()
    assert not ClassMembership.objects.filter(
        user__email="joiner@purdue.edu", klass=two_classes["class_a"]
    ).exists()
