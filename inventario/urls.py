from django.urls import path

from . import views

app_name = "inventario"
urlpatterns = [
    path("activos/<int:pk>/", views.activo_detalle, name="activo_detalle"),
    path("activos/<int:pk>/trasladar/", views.activo_trasladar, name="activo_trasladar"),
    path("activos/<int:pk>/baja/", views.activo_baja, name="activo_baja"),
]
