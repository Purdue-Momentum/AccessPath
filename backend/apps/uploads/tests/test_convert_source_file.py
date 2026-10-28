import pytest
import pymupdf
from unittest.mock import patch

from apps.classes.models import Class, Lecture
from apps.uploads.models import SourceFile, ProcessingJob, ParsedDocument
from apps.uploads.tasks import convert_source_file

@pytest.mark.django_db
@patch("apps.uploads.tasks.put_bytes")
@patch("apps.uploads.tasks.get_bytes")
def test_upload_files_success(
    mock_get_bytes,
    mock_put_bytes,
    client,
    make_user):

  # Creating the sample PDF
  pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 100, 100))
  doc = pymupdf.open()
  page = doc.new_page(width=1000, height=1000)
  page.insert_image(pymupdf.Rect(100, 100, 200, 200), pixmap=pixmap)
  file_bytes = doc.write()
  doc.close()
  mock_get_bytes.return_value = file_bytes

  # Initializing files
  user = make_user()
  klass = Class.objects.create(name="Sample Class", created_by=user)
  lecture = Lecture.objects.create(klass=klass, title="Sample Lecture")

  source_file = SourceFile.objects.create(
    klass=klass,
    lecture=lecture,
    uploaded_by=user,
    original_name="sample.pdf",
    extension=".pdf",
    # Doesn't really matter what is put here--we patch get_bytes
    s3_key="classes/1/uploads/sample.pdf",
    status=SourceFile.Status.UPLOADED
  )

  processing_job = ProcessingJob.objects.create(
    source_file=source_file,
    stage=ProcessingJob.Stage.CONVERT,
    status=ProcessingJob.Status.QUEUED
  )

  convert_source_file(source_file.id)

  source_file.refresh_from_db()
  assert source_file.status == SourceFile.Status.PROCESSING

  convert_job = ProcessingJob.objects.get(
    source_file=source_file,
    stage=ProcessingJob.Stage.CONVERT
  )
  assert convert_job.status == ProcessingJob.Status.SUCCEEDED
  extract_job = ProcessingJob.objects.get(
    source_file=source_file,
    stage=ProcessingJob.Stage.EXTRACT
  )
  assert extract_job.status == ProcessingJob.Status.SUCCEEDED

  # One call for markdown, one for image
  assert mock_put_bytes.call_count == 2

  parsed_document = ParsedDocument.objects.get(source_file=source_file)
  assert str(source_file.klass_id) in parsed_document.markdown_s3_key
  assert "converted" in parsed_document.markdown_s3_key
  assert parsed_document.markdown_s3_key.endswith("sample.md")
  assert len(parsed_document.assets) == 1

  asset = parsed_document.assets[0]
  assert "key" in asset
  assert asset["kind"] == "image"
  assert asset["page"] == 1
  assert asset["box"] == [100.0, 100.0, 200.0, 200.0]
