from rest_framework import serializers

from .models import Export


class ExportSerializer(serializers.ModelSerializer):
    lecture_title = serializers.CharField(source="lecture.title", read_only=True)
    created_by_email = serializers.EmailField(source="created_by.email", read_only=True)

    class Meta:
        model = Export
        fields = ["id", "lecture", "lecture_title", "status", "error", "check_report", "version_ids",
                  "created_by_email", "created_at", "updated_at"]
        read_only_fields = fields


class DownloadSerializer(serializers.Serializer):
    url = serializers.URLField()