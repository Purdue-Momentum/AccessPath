import io
import uuid
import os

from django.utils import timezone
from django.db import transaction

from celery import shared_task
from markitdown import MarkItDown, StreamInfo
import pymupdf

from apps.storage.s3 import get_bytes, class_key, put_bytes
from apps.pipeline.tasks import process_document
from .models import SourceFile, ProcessingJob, ParsedDocument

@shared_task
def convert_source_file(source_file_id: str) -> None:

    # Retrieving file from s3

    try:
        source_file = SourceFile.objects.get(id=source_file_id)
    except SourceFile.DoesNotExist:
        return

    source_file.status = SourceFile.Status.PROCESSING
    source_file.save()

    processing_job = ProcessingJob.objects.get(source_file=source_file, stage=ProcessingJob.Stage.CONVERT, status=ProcessingJob.Status.QUEUED)
    processing_job.status = ProcessingJob.Status.RUNNING
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

    markdown_s3_key = class_key(source_file.klass_id, "converted", file_uuid, f"{stripped_name}.md")
    put_bytes(markdown_s3_key, markdown_bytes, content_type="text/markdown")

    processing_job.status = ProcessingJob.Status.SUCCEEDED
    processing_job.finished_at = timezone.now()
    processing_job.save(update_fields=["finished_at", "status"])

    # Extracting figures and equations

    processing_job = ProcessingJob(
        source_file=source_file,
        stage=ProcessingJob.Stage.EXTRACT,
        status=ProcessingJob.Status.RUNNING,
        started_at=timezone.now()
    )
    processing_job.save()

    assets = []

    if source_file.extension.lower() == ".pdf":
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        for page in doc:
            for image_info in page.get_images():
                xref = image_info[0]
                image = doc.extract_image(xref)
                image_bytes = image["image"]
                
                # Doesn't include the '.', e.g. 'jpeg'
                image_extension = image["ext"]

                image_uuid = uuid.uuid4()
                image_s3_key = class_key(
                    source_file.klass_id,
                    "assets",
                    image_uuid,
                    f"image_p{page.number + 1}-{xref}.{image_extension}"
                )

                put_bytes(image_s3_key, image_bytes, content_type=f"image/{image_extension}")

                rects = page.get_image_rects(xref)

                for rect in rects:
                    assets.append({
                        "key": image_s3_key,
                        "kind": "image",
                        "page": page.number + 1,
                        "box": list(rect)
                    })
    
    processing_job.status = ProcessingJob.Status.SUCCEEDED
    processing_job.finished_at = timezone.now()
    processing_job.save(update_fields=["finished_at", "status"])

    # Creating parsed document and queue apps.pipeline.tasks.process_document

    parsed_document = ParsedDocument(
        source_file=source_file,
        markdown_s3_key=markdown_s3_key,
        assets=assets
    )
    parsed_document.save()

    transaction.on_commit(lambda pd_id=parsed_document.id: process_document.delay(pd_id))