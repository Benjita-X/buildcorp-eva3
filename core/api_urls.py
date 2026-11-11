# URLs de la API REST (todo lo que empieza con /api/)
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api import VIEWSETS  # un ViewSet (CRUD de la API) por cada tabla

# El router crea automáticamente las URLs de cada ViewSet:
# /api/activos/ (listar y crear) y /api/activos/<id>/ (ver, editar y borrar)
router = DefaultRouter()
for prefijo, viewset in VIEWSETS.items():
    router.register(prefijo, viewset, basename=prefijo)

urlpatterns = [
    path("auth/", include("rest_framework.urls")),  # login/logout de la API navegable
    path("", include(router.urls)),
]
