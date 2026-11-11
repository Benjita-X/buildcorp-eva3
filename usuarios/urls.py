from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "usuarios"
urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("mi-clave/", views.CambiarMiClaveView.as_view(), name="mi_clave"),
    path("", views.UsuarioListView.as_view(), name="lista"),
    path("nuevo/", views.UsuarioCreateView.as_view(), name="crear"),
    path("<int:pk>/editar/", views.UsuarioUpdateView.as_view(), name="editar"),
    path("<int:pk>/clave/", views.UsuarioClaveView.as_view(), name="clave"),
]
