"""
Every change to who is in a class goes through these functions.

The main rule: a class must always have at least one active professor.
Postgres cannot express that as a simple constraint, so we lock the class's
professor rows, count what would be left, and refuse if the answer is zero.
"""

import hashlib
import secrets
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Class, ClassMembership, Invite

Role = ClassMembership.Role
Status = ClassMembership.Status


class LastProfessorError(Exception):
    """Raised when a change would leave a class with no active professor."""


class InviteError(Exception):
    """Base class for anything that can go wrong accepting an invite."""


class InviteExpired(InviteError):
    """The invite's expires_at has passed."""


class InviteAlreadyAccepted(InviteError):
    """The invite has already been accepted and cannot be reused."""


class InviteEmailMismatch(InviteError):
    """The accepting user's email does not match the invited email."""


class AlreadyMember(InviteError):
    """The accepting user is already an active member of the class."""


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode()).hexdigest()


def create_invite(*, klass, email, role, invited_by):
    """Mint an invite. Returns (invite, raw_token); only the token's hash is stored."""
    raw_token = secrets.token_urlsafe(32)
    invite = Invite.objects.create(
        klass=klass,
        email=email.strip().lower(),
        role=role,
        token_hash=_hash_token(raw_token),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(hours=settings.INVITE_TTL_HOURS),
    )
    return invite, raw_token


def accept_invite(*, user, raw_token):
    """Accept an invite atomically and create the active membership.

    Raises Invite.DoesNotExist for an unknown token (mapped to 404 by the view)
    and the InviteError subclasses for the various conflict cases.
    """
    with transaction.atomic():
        invite = Invite.objects.select_for_update().get(token_hash=_hash_token(raw_token))

        if invite.expires_at <= timezone.now():
            raise InviteExpired("This invitation has expired.")
        if invite.accepted_at is not None:
            raise InviteAlreadyAccepted("This invitation has already been used.")
        if user.email.lower() != invite.email.lower():
            raise InviteEmailMismatch("This invitation was issued to a different email address.")

        existing = ClassMembership.objects.filter(
            user=user, klass_id=invite.klass_id, status=Status.ACTIVE
        ).first()
        if existing is not None:
            raise AlreadyMember("You are already a member of this class.")

        try:
            membership = ClassMembership.objects.create(
                user=user,
                klass=invite.klass,
                role=invite.role,
                invited_by=invite.invited_by,
                status=Status.ACTIVE,
            )
        except IntegrityError as e:
            raise AlreadyMember("You are already a member of this class.") from e

        invite.accepted_at = timezone.now()
        invite.save(update_fields=["accepted_at", "updated_at"])
    return membership


def create_class(*, user, **fields) -> Class:
    """Create a class. The creator becomes its first professor."""
    with transaction.atomic():
        klass = Class.objects.create(created_by=user, **fields)
        ClassMembership.objects.create(user=user, klass=klass, role=Role.PROFESSOR)
    return klass


def _professors_left_after(membership: ClassMembership, *, new_role=None, new_status=None) -> int:
    # Lock every active professor row in this class so two professors removing
    # each other at the same moment cannot both succeed.
    professors = list(
        ClassMembership.objects.select_for_update()
        .filter(klass_id=membership.klass_id, role=Role.PROFESSOR, status=Status.ACTIVE)
        .values_list("id", flat=True)
    )
    still_professor = (new_role or membership.role) == Role.PROFESSOR and (
        (new_status or membership.status) == Status.ACTIVE
    )
    others = [pk for pk in professors if pk != membership.id]
    return len(others) + (1 if still_professor else 0)


def change_role(membership: ClassMembership, new_role: str) -> ClassMembership:
    with transaction.atomic():
        if _professors_left_after(membership, new_role=new_role) == 0:
            raise LastProfessorError("A class needs at least one professor. Add another professor first.")
        membership.role = new_role
        membership.save(update_fields=["role", "updated_at"])
    return membership


def remove_member(membership: ClassMembership) -> ClassMembership:
    with transaction.atomic():
        if _professors_left_after(membership, new_status=Status.REMOVED) == 0:
            raise LastProfessorError("A class needs at least one professor. Add another professor first.")
        membership.status = Status.REMOVED
        membership.save(update_fields=["status", "updated_at"])
    return membership
