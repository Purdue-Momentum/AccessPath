from rest_framework.permissions import BasePermission

from .models import ClassMembership


def membership_for(user, class_id):
    return ClassMembership.objects.filter(
        user=user, klass_id=class_id, status=ClassMembership.Status.ACTIVE
    ).first()


def is_active_professor(user, class_id) -> bool:
    """True only if the user is an active professor of the class (not just a member)."""
    m = membership_for(user, class_id)
    return m is not None and m.role == ClassMembership.Role.PROFESSOR


class IsClassMember(BasePermission):
    """Allows the request only if the user is an active member of the class in the URL."""

    message = "You are not a member of this class."

    def has_permission(self, request, view):
        class_id = view.kwargs.get("class_id")
        return class_id is not None and membership_for(request.user, class_id) is not None


class IsClassProfessor(BasePermission):
    message = "Only professors in this class can do that."

    def has_permission(self, request, view):
        m = membership_for(request.user, view.kwargs.get("class_id"))
        return m is not None and m.role == ClassMembership.Role.PROFESSOR
