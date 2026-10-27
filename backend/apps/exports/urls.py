from django.urls import path

from . import views

urlpatterns = [
    path("classes/<uuid:class_id>/lectures/<uuid:lecture_id>/exports", views.LectureExportListCreate.as_view(),
         name="export-list"),
    path("classes/<uuid:class_id>/exports/<uuid:export_id>", views.ExportDetail.as_view(), name="export-detail"),
    path("classes/<uuid:class_id>/exports/<uuid:export_id>/download", views.ExportDownload.as_view(),
         name="export-download"),
]