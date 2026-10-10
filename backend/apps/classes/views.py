from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Class, ClassMembership, Lecture
from .permissions import IsClassMember, IsClassProfessor, membership_for
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


class LectureListCreate(generics.ListCreateAPIView):
    serializer_class = LectureSerializer
    permission_classes = [IsClassMember]

    def get_queryset(self):
        return Lecture.objects.filter(klass_id=self.kwargs["class_id"])

    def perform_create(self, serializer):
        serializer.save(klass_id=self.kwargs["class_id"])
