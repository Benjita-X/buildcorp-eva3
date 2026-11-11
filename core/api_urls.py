from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import VIEWSETS, resumen

router = DefaultRouter()
for prefijo, viewset in VIEWSETS.items():
    router.register(prefijo, viewset, basename=prefijo)

urlpatterns = [
    path("resumen/", resumen, name="api_resumen"),
    path("auth/", include("rest_framework.urls")),
    path("", include(router.urls)),
]
