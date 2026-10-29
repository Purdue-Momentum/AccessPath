import uuid
import os
import hashlib
import magic

from django.shortcuts import get_object_or_404
from django.db import transaction

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.storage.s3 import class_key, put_bytes
from apps.classes.models import Class, Lecture
from .models import SourceFile, ProcessingJob
from .tasks import convert_source_file

class UploadFiles(APIView):
    def post(self, request, class_id):

        klass = get_object_or_404(Class, id=class_id)

        lecture_id = request.POST.get("lecture_id")
        if not lecture_id:
            return Response(
                {"error": "No lecture id provided."},
                status=status.HTTP_400_BAD_REQUEST
            )

        lecture = get_object_or_404(Lecture, id=lecture_id)

        files = request.FILES.getlist('files')

        if not files:
            return Response(
                {"error": "No files provided."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        results = []

        for f in files:
            original_name = f.name
            extension = os.path.splitext(original_name)[1]
            size_bytes = f.size
            
            # Inefficient: Struggles with large files
            file_data = f.read()
            sha256_hash = hashlib.sha256(file_data).hexdigest()
            detected_type = magic.from_buffer(file_data, mime=True)

            # Uploading to s3
            file_uuid = uuid.uuid4()
            s3_key = class_key(class_id, "uploads", str(file_uuid), original_name)
            put_bytes(s3_key, file_data, detected_type)

            source_file = SourceFile(
                klass=klass,
                lecture=lecture,
                uploaded_by=request.user,
                original_name=original_name,
                extension=extension,
                detected_type=detected_type,
                size_bytes=size_bytes,
                sha256=sha256_hash,
                s3_key=s3_key,
                status=SourceFile.Status.UPLOADED
            )
            source_file.save()

            results.append({
                "id": source_file.id,
                "filename": source_file.original_name,
                "s3_key": source_file.s3_key
            })

            processing_job = ProcessingJob(
                source_file=source_file,
                stage=ProcessingJob.Stage.CONVERT,
                status=ProcessingJob.Status.QUEUED
            )
            processing_job.save()

            # Parameter necessary because source_file.id
            # will be passed by reference and python
            # doesn't have block scoping for for loops
            transaction.on_commit(lambda sf_id=source_file.id: convert_source_file.delay(sf_id))
        
        return Response({"results": results}, status=status.HTTP_201_CREATED)