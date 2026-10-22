from django.urls import path

from . import views

urlpatterns = [
    path('uploads/classes/<uuid:class_id>/files/', views.UploadFiles.as_view(), name='upload-files')
]