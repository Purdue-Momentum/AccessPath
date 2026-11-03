from django.db import models

from apps.common import BaseModel


class LLMCall(BaseModel):
    """One call to a model. Used to track cost per class and per prompt version."""

    klass = models.ForeignKey("classes.Class", on_delete=models.CASCADE, related_name="llm_calls")
    node = models.ForeignKey("review.Node", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    source_file = models.ForeignKey("uploads.SourceFile", on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="+")
    purpose = models.CharField(max_length=50)  # "process", "describe_image", "equation", "revise"
    model = models.CharField(max_length=100)
    prompt_version = models.CharField(max_length=50)
    input_tokens = models.IntegerField(default=0)
    output_tokens = models.IntegerField(default=0)
    cache_read_tokens = models.IntegerField(default=0)
    cost_usd = models.DecimalField(max_digits=10, decimal_places=6, null=True, default=None)
    latency_ms = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default="unknown")
    error_code = models.CharField(max_length=100, blank=True)
    provider = models.CharField(max_length=30, blank=True)
    provider_request_id = models.CharField(max_length=200, blank=True)


class ProcessingRun(BaseModel):
    """One durable document claim; token prevents an expired worker publishing late."""

    document = models.OneToOneField("uploads.ParsedDocument", on_delete=models.CASCADE, related_name="pipeline_run")
    status = models.CharField(max_length=20, default="queued")
    token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    error = models.TextField(blank=True)


class RevisionDraft(BaseModel):
    """Prepared AI revision. D must apply it and complete review state atomically."""

    node = models.ForeignKey("review.Node", on_delete=models.CASCADE, related_name="ai_revision_drafts")
    base_version = models.ForeignKey("review.NodeVersion", on_delete=models.CASCADE, related_name="+")
    requested_by = models.ForeignKey("accounts.User", on_delete=models.PROTECT, related_name="+")
    comment = models.TextField()
    status = models.CharField(max_length=20, default="queued")
    token = models.UUIDField(null=True)
    lease_until = models.DateTimeField(null=True)
    content = models.JSONField(default=dict)
    model = models.CharField(max_length=100, blank=True)
    error = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(
            fields=["node"], condition=models.Q(status__in=["queued", "running", "ready"]),
            name="one_pending_ai_revision",
        )]


class ProviderSlot(models.Model):
    """Shared per-key throttle across workers using this database; no key is stored."""

    key_hash = models.CharField(max_length=64, primary_key=True)
    next_allowed_at = models.DateTimeField()
