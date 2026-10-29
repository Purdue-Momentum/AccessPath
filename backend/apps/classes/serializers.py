from rest_framework import serializers

from .models import Class, ClassMembership, Invite, Lecture


class ClassSerializer(serializers.ModelSerializer):
    my_role = serializers.SerializerMethodField()

    class Meta:
        model = Class
        fields = ["id", "name", "subject", "course_code", "term", "created_at", "my_role"]
        read_only_fields = ["id", "created_at", "my_role"]

    def get_my_role(self, obj) -> str | None:
        user = self.context["request"].user
        m = obj.memberships.filter(user=user, status=ClassMembership.Status.ACTIVE).first()
        return m.role if m else None


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = ClassMembership
        fields = ["id", "user", "email", "name", "role", "status"]
        read_only_fields = ["id", "user", "email", "name", "status"]


class RoleChangeSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=ClassMembership.Role.choices)


class LectureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Lecture
        fields = ["id", "title", "order", "ta_context", "created_at"]
        read_only_fields = ["id", "created_at"]


class InviteCreateSerializer(serializers.ModelSerializer):
    """Validates invite creation input and exposes the raw token exactly once.

    `token` is read-only and only ever populated by the view on the 201 create
    response; it is never a stored field, so serializing an existing Invite row
    yields no token.
    """

    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=ClassMembership.Role.choices)
    token = serializers.CharField(read_only=True)

    class Meta:
        model = Invite
        fields = ["id", "email", "role", "expires_at", "token"]
        read_only_fields = ["id", "expires_at", "token"]
