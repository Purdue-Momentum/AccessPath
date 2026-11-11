import io
import uuid
import os

from django.utils import timezone
from django.db import transaction

from celery import shared_task
from markitdown import MarkItDown, StreamInfo
import pymupdf
import pptx

from apps.storage.s3 import get_bytes, class_key, put_bytes
from .models import SourceFile, ProcessingJob, ParsedDocument

@shared_task
def convert_source_file(source_file_id: str) -> None:

    # Updating processing job

    source_file = SourceFile.objects.get(id=source_file_id)
    source_file.status = SourceFile.Status.PROCESSING
    source_file.save(update_fields=["status"])

    processing_job = ProcessingJob.objects.get(
        source_file=source_file, 
        stage=ProcessingJob.Stage.CONVERT,
        status=ProcessingJob.Status.QUEUED
    )

    processing_job.status = ProcessingJob.Status.RUNNING
    processing_job.started_at = timezone.now()
    processing_job.save(update_fields=["status", "started_at"])

    # Retrieving file from s3

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

    # Saving markdown to s3

    file_uuid = uuid.uuid4()
    stripped_name = os.path.splitext(source_file.original_name)[0]

    markdown_s3_key = class_key(source_file.klass_id, "converted", file_uuid, f"{stripped_name}.md")
    put_bytes(markdown_s3_key, markdown_bytes, content_type="text/markdown")

    # Marking processing job as complete

    processing_job.status = ProcessingJob.Status.SUCCEEDED
    processing_job.finished_at = timezone.now()
    processing_job.save(update_fields=["finished_at", "status"])

    # Updating parsed document
    ParsedDocument.objects.filter(source_file=source_file).update(
        markdown_s3_key=markdown_s3_key
    )

@shared_task
def extract_source_file(source_file_id: str) -> None:
    
    # Updating processing job

    source_file = SourceFile.objects.get(id=source_file_id)
    source_file.status = SourceFile.Status.PROCESSING
    source_file.save(update_fields=["status"])

    processing_job = ProcessingJob.objects.get(
        source_file=source_file, 
        stage=ProcessingJob.Stage.EXTRACT,
        status=ProcessingJob.Status.QUEUED
    )

    processing_job.status = ProcessingJob.Status.RUNNING
    processing_job.started_at = timezone.now()
    processing_job.save(update_fields=["status", "started_at"])

    # Retrieving file from s3

    file_bytes = get_bytes(source_file.s3_key) 
    stream = io.BytesIO(file_bytes)

    # Extracting figures and equations

    assets = []

    if source_file.extension.lower() == ".pptx":
        
        prs = pptx.Presentation(stream)

        page_number = 1

        # parent is the previous transformation
        # group is the current group
        # Resource: https://stackoverflow.com/a/60776997
        def transform(group, parent):
            el = group._element

            # XML elements' attributes are stored as strings
            # Attempts to find XML attributes in an element
            def find(tag, a, b):
                found = el.xpath(f"./p:grpSpPr/a:xfrm/a:{tag}")
                if not found:
                    return None
                try:
                    return int(found[0].get(a)), int(found[0].get(b))
                except (TypeError, ValueError):
                    return None

            # Offset and extent of group in parent
            off = find("off", "x", "y")
            ext = find("ext", "cx", "cy")
            # Offset and extent of group's children coordinates
            ch_off = find("chOff", "x", "y")
            ch_ext = find("chExt", "cx", "cy")

            if None in (off, ext, ch_off, ch_ext):
                return parent

            # Scale
            gsx = ext[0] / ch_ext[0] if ch_ext[0] else 1.0
            gsy = ext[1] / ch_ext[1] if ch_ext[1] else 1.0

            # Transform
            gtx = off[0] - ch_off[0] * gsx
            gty = off[1] - ch_off[1] * gsy

            psx, psy, ptx, pty = parent
            return (psx * gsx, psy * gsy, psx * gtx + ptx, psy * gty + pty)

        # transformation = (scale_x, scale_y, offset_x, offset_y)
        def parse(shapes, transformation=(1.0, 1.0, 0.0, 0.0)):
            for shape in shapes:
                if shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.GROUP:
                    parse(shape.shapes, transform(shape, transformation))
                elif shape.shape_type == pptx.enum.shapes.MSO_SHAPE_TYPE.PICTURE:
                    image_bytes = shape.image.blob

                    xref = len(assets) + 1

                    image_uuid = uuid.uuid4()
                    image_s3_key = class_key(
                        source_file.klass_id,
                        "assets",
                        image_uuid,
                        f"image_p{page_number}-{xref}.{shape.image.ext}"
                    )

                    put_bytes(image_s3_key, image_bytes, content_type=f"image/{shape.image.content_type}")

                    sx, sy, tx, ty = transformation
                    assets.append({
                        "key": image_s3_key,
                        "kind": "image",
                        "page": page_number,
                        "box": [
                            (shape.left * sx + tx) / pptx.util.Pt(1),
                            (shape.top * sy + ty) / pptx.util.Pt(1),
                            ((shape.left + shape.width) * sx + tx) / pptx.util.Pt(1),
                            ((shape.top + shape.height) * sy + ty) / pptx.util.Pt(1)
                        ]
                    })
    
        for slide in prs.slides:
            parse(slide.shapes)
            page_number += 1

    elif source_file.extension.lower() == ".pdf":
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

    # Updating parsed document

    ParsedDocument.objects.filter(source_file=source_file).update(
        assets=assets
    )