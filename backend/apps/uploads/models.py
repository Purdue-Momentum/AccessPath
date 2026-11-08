from django.conf import settings
from django.db import models

from apps.common import BaseModel


class SourceFile(BaseModel):
    """A raw file a TA uploaded. The original stays in S3 untouched."""

    class Status(models.TextChoices):
        AWAITING_UPLOAD = "awaiting_upload", "Waiting for upload"
        UPLOADED = "uploaded", "Uploaded"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        REJECTED = "rejected", "Rejected"
        FAILED = "failed", "Failed"

    klass = models.ForeignKey("classes.Class", on_delete=models.CASCADE, related_name="source_files")
    lecture = models.ForeignKey("classes.Lecture", on_delete=models.CASCADE, related_name="source_files")
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    original_name = models.CharField(max_length=255)
    extension = models.CharField(max_length=20)
    detected_type = models.CharField(max_length=100, blank=True)  # from reading the file's first bytes
    size_bytes = models.BigIntegerField(default=0)
    sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    s3_key = models.CharField(max_length=500)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.AWAITING_UPLOAD)
    error = models.TextField(blank=True)

    def __str__(self):
        return self.original_name


class ProcessingJob(BaseModel):
    """One step of the pipeline for one file. Lets the upload screen show live progress."""

    class Stage(models.TextChoices):
        CONVERT = "convert", "Convert to Markdown"
        EXTRACT = "extract", "Extract figures and equations"
        PROCESS = "process", "AI processing"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    source_file = models.ForeignKey(SourceFile, on_delete=models.CASCADE, related_name="jobs")
    stage = models.CharField(max_length=20, choices=Stage.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    error = models.TextField(blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)


class ParsedDocument(BaseModel):
    """
    The handoff from Lane B to Lane C.

    markdown_s3_key holds MarkItDown's output. assets lists every extracted figure or
    equation crop, e.g. [{"key": "...", "kind": "image", "page": 3, "box": [x0, y0, x1, y1]}].
    xml_s3_key is filled in by Lane C with exactly what the model returned.
    """

    source_file = models.OneToOneField(SourceFile, on_delete=models.CASCADE, related_name="parsed")
    markdown_s3_key = models.CharField(max_length=500, blank=True)
    assets = models.JSONField(default=list, blank=True)
    xml_s3_key = models.CharField(max_length=500, blank=True)
