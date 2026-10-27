from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(request):
    return JsonResponse({"status": "ok"})


api_v1 = [
    path("", include("apps.accounts.urls")),
    path("", include("apps.classes.urls")),
    path("", include("apps.exports.urls")),
]

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/v1/", include(api_v1)),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
