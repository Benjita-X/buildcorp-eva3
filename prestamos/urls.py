# URLs de la app préstamos (empiezan con /prestamos/)
from django.urls import path

from . import views

app_name = "prestamos"
urlpatterns = [
    path("nuevo/", views.nuevo, name="nuevo"),
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/devolver/", views.devolver, name="devolver"),
]
