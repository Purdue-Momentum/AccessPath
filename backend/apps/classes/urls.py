from django.urls import path

from . import views

urlpatterns = [
    path("classes", views.ClassListCreate.as_view(), name="class-list"),
    path("classes/<uuid:class_id>/members", views.MemberList.as_view(), name="member-list"),
    path("classes/<uuid:class_id>/members/<uuid:membership_id>", views.MemberDetail.as_view(),
         name="member-detail"),
    path("classes/<uuid:class_id>/lectures", views.LectureListCreate.as_view(), name="lecture-list"),
    path("classes/<uuid:class_id>/invites", views.InviteCreate.as_view(), name="invite-create"),
    path("invites/<str:token>/accept", views.InviteAccept.as_view(), name="invite-accept"),
    path("classes/<uuid:class_id>/lectures/<uuid:lecture_id>", views.LectureDetail.as_view(),
         name="lecture-detail"),
]
