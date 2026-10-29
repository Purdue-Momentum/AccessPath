from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from . import services
from .models import Class, ClassMembership, Invite, Lecture
from .permissions import IsClassMember, IsClassProfessor, is_active_professor, membership_for
from .serializers import (
    ClassSerializer,
    InviteCreateSerializer,
    LectureSerializer,
    MembershipSerializer,
    RoleChangeSerializer,
)

User = get_user_model()


class ClassListCreate(generics.ListCreateAPIView):
    """GET my classes. POST creates a class and makes me its professor."""

    serializer_class = ClassSerializer

    def get_queryset(self):
        return Class.objects.filter(
            memberships__user=self.request.user,
            memberships__status=ClassMembership.Status.ACTIVE,
        ).order_by("-created_at")

    def perform_create(self, serializer):
        serializer.instance = services.create_class(user=self.request.user, **serializer.validated_data)


class MemberList(generics.ListAPIView):
    serializer_class = MembershipSerializer
    permission_classes = [IsClassMember]

    def get_queryset(self):
        return ClassMembership.objects.filter(
            klass_id=self.kwargs["class_id"], status=ClassMembership.Status.ACTIVE
        ).select_related("user")


class MemberDetail(APIView):
    """PATCH changes a role. DELETE removes someone. Both refuse to remove the last professor."""

    permission_classes = [IsClassProfessor]

    def _get(self, class_id, membership_id):
        return get_object_or_404(ClassMembership, klass_id=class_id, id=membership_id,
                                 status=ClassMembership.Status.ACTIVE)

    @extend_schema(request=RoleChangeSerializer, responses=MembershipSerializer)
    def patch(self, request, class_id, membership_id):
        membership = self._get(class_id, membership_id)
        role = request.data.get("role")
        if role not in ClassMembership.Role.values:
            return Response({"detail": "Role must be professor or ta."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            services.change_role(membership, role)
        except services.LastProfessorError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(MembershipSerializer(membership).data)

    @extend_schema(responses={204: None, 409: None})
    def delete(self, request, class_id, membership_id):
        membership = self._get(class_id, membership_id)
        try:
            services.remove_member(membership)
        except services.LastProfessorError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(status=status.HTTP_204_NO_CONTENT)


class InviteCreate(APIView):
    """POST creates an invitation to this class. Professor-only; token shown once."""

    permission_classes = [IsClassProfessor]

    @extend_schema(request=InviteCreateSerializer, responses=InviteCreateSerializer)
    def post(self, request, class_id):
        klass = get_object_or_404(Class, id=class_id)
        serializer = InviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"].strip().lower()
        role = serializer.validated_data["role"]

        # If an account already exists for this email and is an active member,
        # there is nothing to invite. (No account yet is fine: invite before signup.)
        existing_user = User.objects.filter(email__iexact=email).first()
        if existing_user is not None and membership_for(existing_user, class_id) is not None:
            return Response(
                {"detail": "That person is already a member of this class."},
                status=status.HTTP_409_CONFLICT,
            )

        invite, raw_token = services.create_invite(
            klass=klass, email=email, role=role, invited_by=request.user
        )
        body = InviteCreateSerializer(invite).data
        body["token"] = raw_token
        return Response(body, status=status.HTTP_201_CREATED)


class InviteAcceptThrottle(ScopedRateThrottle):
    """Rate-limit invite acceptance strictly per client IP.

    ScopedRateThrottle keys authenticated requests by user id, but an attacker
    iterating tokens would do so from a single account, so keying every request
    on the IP catches more of that scripted guessing. We override get_cache_key
    to always use the request IP as the identifier regardless of auth state.
    """

    scope = "invite-accept"

    def get_cache_key(self, request, view):
        if self.rate is None:
            return None
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class InviteAccept(APIView):
    """POST accepts an invitation and creates the membership. Authenticated + email-bound.

    Maps service exceptions to HTTP, mirroring MemberDetail's LastProfessorError -> 409:
    unknown token -> 404, expired -> 410, email mismatch / already-accepted /
    already-member -> 409. Too many attempts from one IP within the window -> 429
    (per-IP throttle to blunt scripted token iteration).
    """

    throttle_classes = [InviteAcceptThrottle]
    throttle_scope = "invite-accept"

    @extend_schema(request=None, responses=MembershipSerializer)
    def post(self, request, token):
        try:
            membership = services.accept_invite(user=request.user, raw_token=token)
        except Invite.DoesNotExist:
            return Response({"detail": "This invitation is not valid."}, status=status.HTTP_404_NOT_FOUND)
        except services.InviteExpired as e:
            return Response({"detail": str(e)}, status=status.HTTP_410_GONE)
        except (services.InviteEmailMismatch, services.InviteAlreadyAccepted, services.AlreadyMember) as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(MembershipSerializer(membership).data, status=status.HTTP_201_CREATED)


class LectureListCreate(generics.ListCreateAPIView):
    serializer_class = LectureSerializer

    def get_permissions(self):
        # Listing stays open to any active member; creating is professor-only.
        if self.request.method == "POST":
            return [IsClassProfessor()]
        return [IsClassMember()]

    def get_queryset(self):
        return Lecture.objects.filter(klass_id=self.kwargs["class_id"])

    def perform_create(self, serializer):
        serializer.save(klass_id=self.kwargs["class_id"])


# Lecture fields only a professor may change. ta_context is editable by TAs too.
PROFESSOR_ONLY_LECTURE_FIELDS = {"title", "order"}


class LectureDetail(APIView):
    """GET/PATCH/DELETE one lecture, scoped to its class so cross-class ids 404.

    PATCH of ta_context is allowed for any active member (professor or TA);
    PATCH touching title/order requires an active professor. DELETE is
    professor-only.
    """

    permission_classes = [IsClassMember]

    def _get(self, class_id, lecture_id):
        return get_object_or_404(Lecture, klass_id=class_id, id=lecture_id)

    @extend_schema(responses=LectureSerializer)
    def get(self, request, class_id, lecture_id):
        lecture = self._get(class_id, lecture_id)
        return Response(LectureSerializer(lecture).data)

    @extend_schema(request=LectureSerializer, responses=LectureSerializer)
    def patch(self, request, class_id, lecture_id):
        lecture = self._get(class_id, lecture_id)
        touches_professor_fields = PROFESSOR_ONLY_LECTURE_FIELDS.intersection(request.data.keys())
        if touches_professor_fields and not is_active_professor(request.user, class_id):
            return Response(
                {"detail": "Only professors can change the title or order of a lecture."},
                status=status.HTTP_403_FORBIDDEN,
            )
        serializer = LectureSerializer(lecture, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @extend_schema(responses={204: None})
    def delete(self, request, class_id, lecture_id):
        lecture = self._get(class_id, lecture_id)
        if not is_active_professor(request.user, class_id):
            return Response(
                {"detail": "Only professors can delete a lecture."},
                status=status.HTTP_403_FORBIDDEN,
            )
        lecture.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
