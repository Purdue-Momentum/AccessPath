import io
import uuid
import os

import math
import numpy as np

from django.utils import timezone
from django.db import transaction

from celery import shared_task
from markitdown import MarkItDown, StreamInfo
import pymupdf

import pptx
from pptx.util import Pt
from pptx.enum.shapes import MSO_SHAPE_TYPE

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

        def translate(tx, ty):
            return np.array([[1, 0, tx],
                             [0, 1, ty],
                             [0, 0, 1 ]], dtype=float)

        def scale(sx, sy):
            return np.array([[sx,  0, 0],
                             [ 0, sy, 0],
                             [ 0,  0, 1]], dtype=float)
        
        def rotate(deg):
            t = math.radians(deg)
            c, s = math.cos(t), math.sin(t)
            return np.array([[c, -s, 0],
                             [s,  c, 0],
                             [0,  0, 1]], dtype=float)

        # parent is the previous transformation
        # group is the current group
        # Resource: https://stackoverflow.com/a/60776997
        def transform(group, parent):

            xfrm = group._element.xpath("./p:grpSpPr/a:xfrm")

            if not xfrm:
                return parent

            xfrm = xfrm[0]

            # XML elements' attributes are stored as strings
            # Attempts to find XML attributes in an element
            def find(tag, a, b):
                found = xfrm.xpath(f"./a:{tag}")
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

            # Rotation
            try:
                rot = int(xfrm.get("rot", "0")) / 60000
            except ValueError:
                rot = 0.0
            
            # Flip
            fh = xfrm.get("flipH") in ("1", "true")
            fv = xfrm.get("flipV") in ("1", "true")

            # Scale
            sx = ext[0] / ch_ext[0] if ch_ext[0] else 1.0
            sy = ext[1] / ch_ext[1] if ch_ext[1] else 1.0

            m = np.eye(3)

            # Stretch
            m = np.matmul(translate(-ch_off[0], -ch_off[1]), m)
            m = np.matmul(scale(sx, sy), m)

            cx = ext[0] / 2
            cy = ext[1] / 2

            # Flip and rotate
            m = np.matmul(translate(-cx, -cy), m)
            m = np.matmul(scale(-1 if fh else 1, -1 if fv else 1), m)
            m = np.matmul(rotate(rot), m)
            m = np.matmul(translate(cx, cy), m)

            # Translate
            m = np.matmul(translate(off[0], off[1]), m)

            return np.matmul(parent, m)

        def parse(shapes, transformation=np.eye(3)):
            for shape in shapes:
                if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                    parse(shape.shapes, transform(shape, transformation))
                elif shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                    image_bytes = shape.image.blob

                    xref = len(assets) + 1

                    image_uuid = uuid.uuid4()
                    image_s3_key = class_key(
                        source_file.klass_id,
                        "assets",
                        image_uuid,
                        f"image_p{page_number}-{xref}.{shape.image.ext}"
                    )

                    put_bytes(image_s3_key, image_bytes, content_type=shape.image.content_type)

                    left = shape.left
                    right = left + shape.width
                    top = shape.top
                    bottom = top + shape.height

                    points = np.array([[left, right,  right,   left],
                                       [ top,   top, bottom, bottom],
                                       [   1,     1,      1,      1]], dtype=float)

                    cx = (left + right) / 2
                    cy = (top + bottom) / 2

                    m = np.eye(3)

                    # Rotate by picture's own rotation
                    m = np.matmul(translate(-cx, -cy), m)
                    m = np.matmul(rotate(shape.rotation), m)
                    m = np.matmul(translate(cx, cy), m)
                    
                    # Compose with parent transformation
                    m = np.matmul(transformation, m)
                    
                    points = np.matmul(m, points)
                    # Rectangle configuration doesn't really support rotations
                    # so we just take the topmost, leftmost, bottommost, and
                    # rightmost x and y coordinates
                    xs = points[0]
                    ys = points[1]

                    assets.append({
                        "key": image_s3_key,
                        "kind": "image",
                        "page": page_number,
                        "box": [
                            float(xs.min() / Pt(1)),
                            float(ys.min() / Pt(1)),
                            float(xs.max() / Pt(1)),
                            float(ys.max() / Pt(1)),
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