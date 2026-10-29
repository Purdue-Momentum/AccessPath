import pytest
from unittest.mock import patch
from rest_framework import status

from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.classes.models import Class, Lecture
from apps.uploads.models import SourceFile

@pytest.mark.django_db
@patch("apps.uploads.views.put_bytes")
def test_upload_files_success(mock_put_bytes, client, make_user):
  user = make_user()
  client.force_login(user=user)

  klass = Class.objects.create(name="Sample Class", created_by=user)
  lecture = Lecture.objects.create(klass=klass, title="Sample Lecture")

  url = reverse('upload-files', kwargs={'class_id': klass.id})

  filename = "sample.txt"
  file_content = b"something something something"
  content_type = "text/plain"

  uploaded_file = SimpleUploadedFile(
    name=filename,
    content=file_content,
    content_type=content_type
  )

  data = {
    'lecture_id': lecture.id,
    'files': [uploaded_file]
  }

  response = client.post(url, data, format="multipart")

  assert response.status_code == status.HTTP_201_CREATED
  assert len(response.data['results']) == 1
  assert response.data['results'][0]['filename'] == "sample.txt"

  assert SourceFile.objects.count() == 1
  source_file = SourceFile.objects.first()

  assert source_file.lecture == lecture
  assert source_file.klass == klass
  assert source_file.uploaded_by == user

  assert source_file.original_name == filename
  assert source_file.extension == ".txt"
  assert source_file.detected_type == content_type

  assert source_file.size_bytes == len(file_content)
  assert source_file.status == SourceFile.Status.UPLOADED

  mock_put_bytes.assert_called_once()
