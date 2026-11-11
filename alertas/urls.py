# URLs de la app alertas (empiezan con /alertas/)
from django.urls import path

from . import views

app_name = "alertas"
urlpatterns = [
    path("", views.lista, name="lista"),
    path("revisar/", views.revisar, name="revisar"),
    path("<int:pk>/resolver/", views.resolver, name="resolver"),
]
