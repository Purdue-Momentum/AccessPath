from django.urls import path

from . import views

urlpatterns = [
    path("classes/<uuid:class_id>/nodes", views.NodeListView.as_view(), name="node-list"),
    path("classes/<uuid:class_id>/queue", views.ReviewQueueView.as_view(), name="review-queue"),
    path("classes/<uuid:class_id>/nodes/bulk-approve", views.BulkApproveView.as_view(), name="node-bulk-approve"),
    path("nodes/<uuid:node_id>", views.NodeDetailView.as_view(), name="node-detail"),
    path("nodes/<uuid:node_id>/versions", views.NodeVersionCreateView.as_view(), name="node-version-create"),
    path("nodes/<uuid:node_id>/approve", views.NodeApproveView.as_view(), name="node-approve"),
    path("nodes/<uuid:node_id>/flag", views.NodeFlagView.as_view(), name="node-flag"),
    path("nodes/<uuid:node_id>/unflag", views.NodeUnflagView.as_view(), name="node-unflag"),
    path("nodes/<uuid:node_id>/send-back", views.NodeSendBackView.as_view(), name="node-send-back"),
    path("nodes/<uuid:node_id>/regenerate", views.NodeRegenerateView.as_view(), name="node-regenerate"),
]
