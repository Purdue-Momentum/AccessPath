"""Lane B. Celery tasks on the convert queue."""

from django.utils import timezone

from celery import shared_task
from markitdown import MarkItDown, StreamInfo

from apps.storage.s3 import get_bytes, class_key, put_bytes
from .model import SourceFile, ProcessingJob

@shared_task
def convert_source_file(source_file_id: str) -> None:

    # Retrieving file from s3

    try:
        source_file = SourceFile.objects.get(id=source_file_id)
    except SourceFile.DoesNotExist:
        return f"Source file {source_file_id} not found, skipping"

    source_file.status = SourceFile.Status.PROCESSING
    source_file.save()

    processing_job = ProcessingJob.objects.get(source_file=source_file, stage=SourceFile.Stage.CONVERT, status=SourceFile.Status.QUEUED)
    processing_job.status = SourceFile.Status.RUNNING
    processing_job.started_at = timezone.now()
    processing_job.save(update_fields=["status", "started_at"])

    file_bytes = get_bytes(source_file.s3_key) 
    stream = io.BytesIO(file_bytes)

    # Converting file to markdown

    md = MarkItDown()
    result = md.convert_stream(
        stream,
        stream_info=StreamInfo(extension=source_file.extension)
    )
    markdown_content = result.markdown
    markdown_bytes = markdown_content.encode()

    file_uuid = uuid.uuid4()
    stripped_name = os.path.splitext(source_file.original_name)[0]

    s3_key = class_key(source_file.klass_id, "converted", file_uuid, stripped_name)
    put_bytes(s3_key, markdown_bytes, content_type="text/markdown")

    processing_job.finished_at = timezone.now()
    processing_job.save(update_fields=["finished_at"])

    # Extracting figures and equations

    processing_job = ProcessingJob(
        source_files=source_file,
        stage=ProcessingJob.Stage.EXTRACT,
        status=ProcessingJob.Status.RUNNING,
        started_at=timezone.now()
    )

    # Creating parsed document and queue apps.pipeline.tasks.process_document.

    raise NotImplementedError
