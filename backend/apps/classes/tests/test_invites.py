import hashlib
from datetime import timedelta

import pytest
from django.conf import settings
from django.utils import timezone

from apps.classes import services
from apps.classes.models import Class, ClassMembership, Invite

Role = ClassMembership.Role
Status = ClassMembership.Status


@pytest.fixture
def klass(make_user):
    prof = make_user("prof@purdue.edu")
    return services.create_class(user=prof, name="Dynamics", course_code="ME 27400")


# --- Slice 1: service layer -------------------------------------------------


def test_create_invite_returns_token_and_stores_only_hash(klass):
    prof = klass.created_by
    invite, raw_token = services.create_invite(
        klass=klass, email="ta@purdue.edu", role=Role.TA, invited_by=prof
    )
    assert raw_token
    assert invite.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    assert len(invite.token_hash) == 64
    # The raw token must not be persisted on any field of the row.
    invite.refresh_from_db()
    for value in invite.__dict__.values():
        assert value != raw_token


def test_create_invite_tokens_are_random(klass):
    prof = klass.created_by
    _, token_a = services.create_invite(klass=klass, email="a@purdue.edu", role=Role.TA, invited_by=prof)
    _, token_b = services.create_invite(klass=klass, email="b@purdue.edu", role=Role.TA, invited_by=prof)
    assert token_a != token_b


def test_create_invite_expiry_from_setting(klass):
    prof = klass.created_by
    before = timezone.now()
    invite, _ = services.create_invite(klass=klass, email="ta@purdue.edu", role=Role.TA, invited_by=prof)
    expected = before + timedelta(hours=settings.INVITE_TTL_HOURS)
    assert abs((invite.expires_at - expected).total_seconds()) < 30


def test_create_invite_normalizes_email(klass):
    prof = klass.created_by
    invite, _ = services.create_invite(klass=klass, email="  TA@Purdue.edu ", role=Role.TA, invited_by=prof)
    assert invite.email == "ta@purdue.edu"


def test_accept_invite_happy_path(klass, make_user):
    prof = klass.created_by
    ta_user = make_user("ta@purdue.edu")
    invite, raw_token = services.create_invite(
        klass=klass, email="ta@purdue.edu", role=Role.TA, invited_by=prof
    )
    membership = services.accept_invite(user=ta_user, raw_token=raw_token)
    assert membership.klass_id == klass.id
    assert membership.role == Role.TA
    assert membership.status == Status.ACTIVE
    assert membership.invited_by_id == prof.id
    invite.refresh_from_db()
    assert invite.accepted_at is not None


def test_accept_invite_expired(klass, make_user):
    prof = klass.created_by
    ta_user = make_user("ta@purdue.edu")
    invite, raw_token = services.create_invite(
        klass=klass, email="ta@purdue.edu", role=Role.TA, invited_by=prof
    )
    invite.expires_at = timezone.now() - timedelta(hours=1)
    invite.save(update_fields=["expires_at"])
    with pytest.raises(services.InviteExpired):
        services.accept_invite(user=ta_user, raw_token=raw_token)


def test_accept_invite_already_accepted(klass, make_user):
    prof = klass.created_by
    ta_user = make_user("ta@purdue.edu")
    invite, raw_token = services.create_invite(
        klass=klass, email="ta@purdue.edu", role=Role.TA, invited_by=prof
    )
    services.accept_invite(user=ta_user, raw_token=raw_token)
    with pytest.raises(services.InviteAlreadyAccepted):
        services.accept_invite(user=ta_user, raw_token=raw_token)


def test_accept_invite_email_mismatch(klass, make_user):
    prof = klass.created_by
    other = make_user("someoneelse@purdue.edu")
    _, raw_token = services.create_invite(klass=klass, email="ta@purdue.edu", role=Role.TA, invited_by=prof)
    with pytest.raises(services.InviteEmailMismatch):
        services.accept_invite(user=other, raw_token=raw_token)


def test_accept_invite_already_member(klass, make_user):
    prof = klass.created_by
    # The professor who created the class is already an active member.
    _, raw_token = services.create_invite(klass=klass, email=prof.email, role=Role.TA, invited_by=prof)
    with pytest.raises(services.AlreadyMember):
        services.accept_invite(user=prof, raw_token=raw_token)


# --- Slice 2: invite create endpoint ----------------------------------------

PASSWORD = "a-good-password-123"


def _login(api, email):
    res = api.post("/api/v1/auth/login", {"email": email, "password": PASSWORD})
    assert res.status_code == 200


def _make_class(api, make_user, email="prof@purdue.edu"):
    make_user(email)
    _login(api, email)
    res = api.post("/api/v1/classes", {"name": "Dynamics", "course_code": "ME 27400"})
    assert res.status_code == 201
    return res.data["id"]


@pytest.mark.django_db
def test_invite_create_professor_201_token_once(api, make_user):
    class_id = _make_class(api, make_user)
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": "ta@purdue.edu", "role": "ta"})
    assert res.status_code == 201
    assert set(["id", "email", "role", "expires_at", "token"]).issubset(res.data.keys())
    assert res.data["email"] == "ta@purdue.edu"
    assert res.data["role"] == "ta"
    raw_token = res.data["token"]
    assert raw_token

    invite = Invite.objects.get(id=res.data["id"])
    assert invite.token_hash == hashlib.sha256(raw_token.encode()).hexdigest()
    # The raw token is never persisted on the row.
    for value in invite.__dict__.values():
        assert value != raw_token


@pytest.mark.django_db
def test_invite_create_response_serializer_has_no_token_on_read(api, make_user):
    from apps.classes.serializers import InviteCreateSerializer

    class_id = _make_class(api, make_user)
    invite, _ = services.create_invite(
        klass=Class.objects.get(id=class_id), email="ta@purdue.edu", role=Role.TA,
        invited_by=make_user("another@purdue.edu"),
    )
    # Serializing an existing invite instance must not expose a token value.
    data = InviteCreateSerializer(invite).data
    assert not data.get("token")


@pytest.mark.django_db
def test_invite_create_ta_member_forbidden(api, make_user):
    class_id = _make_class(api, make_user)
    ta = make_user("ta@purdue.edu")
    ClassMembership.objects.create(user=ta, klass_id=class_id, role=Role.TA)
    api.post("/api/v1/auth/logout")
    _login(api, "ta@purdue.edu")
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": "new@purdue.edu", "role": "ta"})
    assert res.status_code == 403


@pytest.mark.django_db
def test_invite_create_outsider_forbidden(api, make_user):
    class_id = _make_class(api, make_user)
    make_user("outsider@purdue.edu")
    api.post("/api/v1/auth/logout")
    _login(api, "outsider@purdue.edu")
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": "new@purdue.edu", "role": "ta"})
    assert res.status_code == 403


@pytest.mark.django_db
def test_invite_create_invalid_role_400(api, make_user):
    class_id = _make_class(api, make_user)
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": "ta@purdue.edu", "role": "student"})
    assert res.status_code == 400


@pytest.mark.django_db
def test_invite_create_invalid_email_400(api, make_user):
    class_id = _make_class(api, make_user)
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": "not-an-email", "role": "ta"})
    assert res.status_code == 400


@pytest.mark.django_db
def test_invite_create_existing_active_member_409(api, make_user):
    class_id = _make_class(api, make_user)
    existing = make_user("ta@purdue.edu")
    ClassMembership.objects.create(user=existing, klass_id=class_id, role=Role.TA)
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": "ta@purdue.edu", "role": "ta"})
    assert res.status_code == 409


# --- Slice 3: invite accept endpoint ----------------------------------------


def _mint_invite_token(api, make_user, email, role="ta"):
    """Create a class as the professor, invite `email`, return (class_id, token)."""
    class_id = _make_class(api, make_user)
    res = api.post(f"/api/v1/classes/{class_id}/invites", {"email": email, "role": role})
    assert res.status_code == 201
    api.post("/api/v1/auth/logout")
    return class_id, res.data["token"]


@pytest.mark.django_db
def test_invite_accept_matching_email_becomes_member(api, make_user):
    class_id, token = _mint_invite_token(api, make_user, "ta@purdue.edu", role="ta")
    make_user("ta@purdue.edu")
    _login(api, "ta@purdue.edu")
    res = api.post(f"/api/v1/invites/{token}/accept")
    assert res.status_code in (200, 201)
    membership = ClassMembership.objects.get(klass_id=class_id, user__email="ta@purdue.edu")
    assert membership.role == Role.TA
    assert membership.status == Status.ACTIVE
    invite = Invite.objects.get(klass_id=class_id)
    assert invite.accepted_at is not None


@pytest.mark.django_db
def test_invite_accept_role_comes_from_invite(api, make_user):
    class_id, token = _mint_invite_token(api, make_user, "newprof@purdue.edu", role="professor")
    make_user("newprof@purdue.edu")
    _login(api, "newprof@purdue.edu")
    res = api.post(f"/api/v1/invites/{token}/accept")
    assert res.status_code in (200, 201)
    membership = ClassMembership.objects.get(klass_id=class_id, user__email="newprof@purdue.edu")
    assert membership.role == Role.PROFESSOR


@pytest.mark.django_db
def test_invite_accept_wrong_email_409(api, make_user):
    _, token = _mint_invite_token(api, make_user, "ta@purdue.edu")
    make_user("wrong@purdue.edu")
    _login(api, "wrong@purdue.edu")
    res = api.post(f"/api/v1/invites/{token}/accept")
    assert res.status_code == 409


@pytest.mark.django_db
def test_invite_accept_expired_410(api, make_user):
    class_id, token = _mint_invite_token(api, make_user, "ta@purdue.edu")
    invite = Invite.objects.get(klass_id=class_id)
    invite.expires_at = timezone.now() - timedelta(hours=1)
    invite.save(update_fields=["expires_at"])
    make_user("ta@purdue.edu")
    _login(api, "ta@purdue.edu")
    res = api.post(f"/api/v1/invites/{token}/accept")
    assert res.status_code == 410


@pytest.mark.django_db
def test_invite_accept_reused_409(api, make_user):
    _, token = _mint_invite_token(api, make_user, "ta@purdue.edu")
    make_user("ta@purdue.edu")
    _login(api, "ta@purdue.edu")
    first = api.post(f"/api/v1/invites/{token}/accept")
    assert first.status_code in (200, 201)
    second = api.post(f"/api/v1/invites/{token}/accept")
    assert second.status_code == 409


@pytest.mark.django_db
def test_invite_accept_unknown_token_404(api, make_user):
    make_user("ta@purdue.edu")
    _login(api, "ta@purdue.edu")
    res = api.post("/api/v1/invites/this-token-does-not-exist/accept")
    assert res.status_code == 404


@pytest.mark.django_db
def test_invite_accept_unauthenticated_rejected(api, make_user):
    _, token = _mint_invite_token(api, make_user, "ta@purdue.edu")
    # No login after logout inside _mint_invite_token.
    res = api.post(f"/api/v1/invites/{token}/accept")
    assert res.status_code in (401, 403)
