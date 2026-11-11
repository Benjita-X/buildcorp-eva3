from django.urls import path

from . import views

app_name = "mantenimiento"
urlpatterns = [
    path("ot/<int:pk>/", views.detalle, name="detalle"),
    path("ot/<int:pk>/iniciar/", views.iniciar, name="iniciar"),
    path("ot/<int:pk>/completar/", views.completar, name="completar"),
    path("ot/<int:pk>/cancelar/", views.cancelar, name="cancelar"),
]
