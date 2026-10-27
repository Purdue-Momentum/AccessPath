from django.contrib import admin

from .models import Export


@admin.register(Export)
class ExportAdmin(admin.ModelAdmin):
    list_display = ["lecture", "klass", "status", "created_by", "created_at"]
    list_filter = ["status"]
    readonly_fields = ["html_s3_key", "version_ids", "error", "check_report"]