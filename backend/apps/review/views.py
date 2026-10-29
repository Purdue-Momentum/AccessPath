from django.db import transaction
from django.db.models import F, Max
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.classes.models import ClassMembership
from apps.classes.permissions import IsClassMember, IsClassProfessor, membership_for

from .models import Comment, Node, NodeVersion, ReviewAction
from .serializers import (
    ActionInputSerializer,
    BulkApproveInputSerializer,
    CommentSerializer,
    NodeDetailSerializer,
    NodeSerializer,
    NodeVersionSerializer,
    VersionCreateInputSerializer,
)
from .state_machine import TransitionError, bulk_approve, transition


def get_node_and_membership(user, node_id):
    node = get_object_or_404(
        Node.objects.select_related("current_version"),
        id=node_id,
    )
    membership = membership_for(user, node.klass_id)
    if membership is None:
        raise PermissionDenied("You are not a member of this class.")
    return node, membership


class NodeListView(generics.ListAPIView):
    """GET all nodes in a class, with optional filtering by state, lecture, or kind."""

    serializer_class = NodeSerializer
    permission_classes = [IsClassMember]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="state", type=str, required=False),
            OpenApiParameter(name="lecture", type=str, required=False),
            OpenApiParameter(name="kind", type=str, required=False),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        qs = Node.objects.filter(klass_id=self.kwargs["class_id"]).select_related("current_version")
        state = self.request.query_params.get("state")
        lecture = self.request.query_params.get("lecture")
        kind = self.request.query_params.get("kind")
        if state:
            qs = qs.filter(state=state)
        if lecture:
            qs = qs.filter(lecture_id=lecture)
        if kind:
            qs = qs.filter(kind=kind)
        return qs.order_by("lecture", "order")


class ReviewQueueView(generics.ListAPIView):
    """GET the review queue for a class based on the user's role (TA vs Professor), lowest confidence first."""

    serializer_class = NodeSerializer
    permission_classes = [IsClassMember]

    def get_queryset(self):
        class_id = self.kwargs["class_id"]
        membership = membership_for(self.request.user, class_id)
        if membership.role == ClassMembership.Role.TA:
            target_state = Node.State.TA_REVIEW
        else:
            target_state = Node.State.PROF_REVIEW

        return (
            Node.objects.filter(klass_id=class_id, state=target_state)
            .select_related("current_version")
            .order_by(F("confidence").asc(nulls_first=True), "order")
        )


class NodeDetailView(APIView):
    """GET a single node with its current_version, version history, comments, and audit actions."""

    @extend_schema(responses=NodeDetailSerializer)
    def get(self, request, node_id):
        node, _ = get_node_and_membership(request.user, node_id)
        return Response(NodeDetailSerializer(node).data)


class NodeVersionCreateView(APIView):
    """POST a new version of a node (append-only) and point current_version to it."""

    @extend_schema(request=VersionCreateInputSerializer, responses={201: NodeDetailSerializer})
    def post(self, request, node_id):
        node, membership = get_node_and_membership(request.user, node_id)
        serializer = VersionCreateInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            if node.state in (Node.State.TA_REVIEW, Node.State.PROF_REVIEW):
                try:
                    transition(
                        node,
                        ReviewAction.Action.EDIT,
                        actor=request.user,
                        role=membership.role,
                        comment=serializer.validated_data.get("note", ""),
                    )
                except TransitionError as e:
                    return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

            max_num = node.versions.aggregate(m=Max("number"))["m"] or 0
            new_version = NodeVersion.objects.create(
                node=node,
                number=max_num + 1,
                content=serializer.validated_data["content"],
                extra=serializer.validated_data.get("extra", {}),
                author_type=NodeVersion.AuthorType.PERSON,
                author=request.user,
                note=serializer.validated_data.get("note", ""),
            )
            node.current_version = new_version
            node.save(update_fields=["current_version", "updated_at"])

        node.refresh_from_db()
        return Response(NodeDetailSerializer(node).data, status=status.HTTP_201_CREATED)


class BaseNodeActionView(APIView):
    action_name = None

    @extend_schema(request=ActionInputSerializer, responses=NodeDetailSerializer)
    def post(self, request, node_id):
        node, membership = get_node_and_membership(request.user, node_id)
        serializer = ActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = serializer.validated_data.get("comment", "")

        try:
            with transaction.atomic():
                transition(
                    node,
                    self.action_name,
                    actor=request.user,
                    role=membership.role,
                    comment=comment,
                )
                if comment.strip():
                    Comment.objects.create(
                        node=node,
                        version=node.current_version,
                        author=request.user,
                        text=comment.strip(),
                    )
        except TransitionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        node.refresh_from_db()
        return Response(NodeDetailSerializer(node).data)


class NodeApproveView(BaseNodeActionView):
    """POST to approve a node (TA moves to prof_review; Professor moves to approved)."""
    action_name = ReviewAction.Action.APPROVE


class NodeFlagView(BaseNodeActionView):
    """POST to flag a node in ta_review."""
    action_name = ReviewAction.Action.FLAG


class NodeUnflagView(BaseNodeActionView):
    """POST to unflag a flagged node back to ta_review."""
    action_name = ReviewAction.Action.UNFLAG


class NodeSendBackView(BaseNodeActionView):
    """POST for a professor to send a node back for revision (requires comment)."""
    action_name = ReviewAction.Action.SEND_BACK


class NodeRegenerateView(BaseNodeActionView):
    """POST to send a node back to processing for AI regeneration."""
    action_name = ReviewAction.Action.REGENERATE


class BulkApproveView(APIView):
    """POST for a professor to approve multiple nodes in prof_review at once."""

    permission_classes = [IsClassProfessor]

    @extend_schema(request=BulkApproveInputSerializer, responses=NodeSerializer(many=True))
    def post(self, request, class_id):
        serializer = BulkApproveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        node_ids = serializer.validated_data["node_ids"]

        nodes = list(Node.objects.filter(klass_id=class_id, id__in=node_ids).select_related("current_version"))
        if len(nodes) != len(set(node_ids)):
            return Response(
                {"detail": "One or more nodes were not found in this class."},
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            bulk_approve(nodes, actor=request.user)
        except TransitionError as e:
            return Response({"detail": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(NodeSerializer(nodes, many=True).data)
