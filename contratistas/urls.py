from django.urls import path

from . import views

app_name = "contratistas"
urlpatterns = [
    path("<int:pk>/", views.detalle, name="detalle"),
    path("<int:pk>/bloquear/", views.bloquear, name="bloquear"),
    path("<int:pk>/desbloquear/", views.desbloquear, name="desbloquear"),
]
