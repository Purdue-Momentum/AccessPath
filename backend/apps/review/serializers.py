from rest_framework import serializers

from .models import Comment, Node, NodeVersion, ReviewAction


class NodeVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeVersion
        fields = [
            "id",
            "node",
            "number",
            "content",
            "extra",
            "author_type",
            "author",
            "model",
            "prompt_version",
            "note",
            "created_at",
        ]
        read_only_fields = ["id", "node", "number", "author", "created_at"]


class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ["id", "node", "version", "author", "text", "resolved", "created_at"]
        read_only_fields = ["id", "node", "author", "created_at"]


class ReviewActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewAction
        fields = [
            "id",
            "node",
            "version",
            "actor",
            "role",
            "action",
            "comment",
            "from_state",
            "to_state",
            "created_at",
        ]
        read_only_fields = fields


class NodeSerializer(serializers.ModelSerializer):
    current_version = NodeVersionSerializer(read_only=True)

    class Meta:
        model = Node
        fields = [
            "id",
            "klass",
            "lecture",
            "document",
            "order",
            "kind",
            "state",
            "confidence",
            "assignee",
            "current_version",
            "flag_reason",
            "source_ref",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class NodeDetailSerializer(serializers.ModelSerializer):
    current_version = NodeVersionSerializer(read_only=True)
    versions = NodeVersionSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    actions = ReviewActionSerializer(many=True, read_only=True)

    class Meta:
        model = Node
        fields = [
            "id",
            "klass",
            "lecture",
            "document",
            "order",
            "kind",
            "state",
            "confidence",
            "assignee",
            "current_version",
            "flag_reason",
            "source_ref",
            "versions",
            "comments",
            "actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ActionInputSerializer(serializers.Serializer):
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class BulkApproveInputSerializer(serializers.Serializer):
    node_ids = serializers.ListField(
        child=serializers.UUIDField(),
        allow_empty=False,
        help_text="List of node UUIDs to bulk approve.",
    )


class VersionCreateInputSerializer(serializers.Serializer):
    content = serializers.CharField()
    extra = serializers.JSONField(required=False, default=dict)
    note = serializers.CharField(required=False, allow_blank=True, default="")
