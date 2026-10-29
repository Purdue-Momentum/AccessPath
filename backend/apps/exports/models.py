from django.conf import settings
from django.db import models

from apps.common import BaseModel


class Export(BaseModel):
    """An accessible HTML export of one lecture. HTML is the only export format."""

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    klass = models.ForeignKey("classes.Class", on_delete=models.CASCADE, related_name="exports")
    lecture = models.ForeignKey("classes.Lecture", on_delete=models.CASCADE, related_name="exports")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    html_s3_key = models.CharField(max_length=500, blank=True)
    # The exact NodeVersion ids that went into this export, so it can be reproduced later.
    version_ids = models.JSONField(default=list, blank=True)
    error = models.TextField(blank=True)    #reason for error
    # Accessibility check results: [{"level": "warning", "rule": "..", "message": ".."}]
    check_report = models.JSONField(default=list, blank=True) 

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Export of {self.lecture} ({self.status})"