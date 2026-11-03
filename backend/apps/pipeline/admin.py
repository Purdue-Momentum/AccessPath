from django.contrib import admin

from .models import LLMCall, ProcessingRun, RevisionDraft


@admin.register(LLMCall)
class LLMCallAdmin(admin.ModelAdmin):
    list_display = ["purpose", "model", "prompt_version", "input_tokens", "output_tokens",
                    "cost_usd", "status", "created_at"]
    list_filter = ["purpose", "model"]


@admin.register(ProcessingRun)
class ProcessingRunAdmin(admin.ModelAdmin):
    list_display = ["document", "status", "error", "updated_at"]
    readonly_fields = [field.name for field in ProcessingRun._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RevisionDraft)
class RevisionDraftAdmin(admin.ModelAdmin):
    list_display = ["node", "status", "requested_by", "error", "updated_at"]
    readonly_fields = [field.name for field in RevisionDraft._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
