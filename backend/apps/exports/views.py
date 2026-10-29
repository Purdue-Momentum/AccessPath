from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.classes.models import Lecture
from apps.classes.permissions import IsClassMember
from apps.storage import s3

from . import services
from .models import Export
from .rendering import ExportError
from .serializers import DownloadSerializer, ExportSerializer


class LectureExportListCreate(APIView):
    """GET this lecture's exports, newest first. POST starts a new export of the lecture."""

    permission_classes = [IsAuthenticated, IsClassMember]  # IsAuthenticated first, or logged out is a 500

    def _lecture(self, class_id, lecture_id):
        return get_object_or_404(Lecture, id=lecture_id, klass_id=class_id)

    @extend_schema(responses=ExportSerializer(many=True))
    def get(self, request, class_id, lecture_id):
        lecture = self._lecture(class_id, lecture_id)
        exports = Export.objects.filter(lecture=lecture).select_related("lecture", "created_by")
        return Response(ExportSerializer(exports, many=True).data)

    @extend_schema(request=None, responses={202: ExportSerializer, 409: None})
    def post(self, request, class_id, lecture_id):
        lecture = self._lecture(class_id, lecture_id)
        try:
            export = services.start_export(lecture=lecture, user=request.user)
        except ExportError as e:
            return Response({"detail": str(e)}, status=status.HTTP_409_CONFLICT)
        return Response(ExportSerializer(export).data, status=status.HTTP_202_ACCEPTED)


class ExportDetail(APIView):
    """GET one export. The frontend polls this until status is done or failed."""

    permission_classes = [IsAuthenticated, IsClassMember]  # IsAuthenticated first, or logged out is a 500

    @extend_schema(responses=ExportSerializer)
    def get(self, request, class_id, export_id):
        export = get_object_or_404(Export.objects.select_related("lecture", "created_by"),
                                   id=export_id, klass_id=class_id)
        return Response(ExportSerializer(export).data)


class ExportDownload(APIView):
    """GET a short lived link to the finished HTML file."""

    permission_classes = [IsAuthenticated, IsClassMember]  # IsAuthenticated first, or logged out is a 500

    @extend_schema(responses={200: DownloadSerializer, 409: None})
    def get(self, request, class_id, export_id):
        export = get_object_or_404(Export.objects.select_related("lecture"), id=export_id, klass_id=class_id)
        if export.status != Export.Status.DONE:
            return Response({"detail": "This export is not finished."}, status=status.HTTP_409_CONFLICT)
        filename = f"{slugify(export.lecture.title) or 'lecture'}.html"
        return Response({"url": s3.presign_download(export.html_s3_key, filename=filename)})