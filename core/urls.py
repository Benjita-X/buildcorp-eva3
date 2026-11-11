# URLs de la app core: el dashboard y los mantenedores de cada tabla
from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),                       # pantalla principal
    path("mantenedores/", views.parametrizacion, name="mantenedores"),  # página "Parametrización"
    # Mantenedores genéricos (uno por tabla), todos con los mismos templates
    # <slug> es el nombre de la tabla en la URL, por ejemplo /m/comunas/
    path("m/<slug:slug>/", views.CrudListView.as_view(), name="crud_lista"),                     # listar
    path("m/<slug:slug>/nuevo/", views.CrudFormView.as_view(), name="crud_crear"),               # crear
    path("m/<slug:slug>/<int:pk>/", views.CrudDetailView.as_view(), name="crud_detalle"),        # ver
    path("m/<slug:slug>/<int:pk>/editar/", views.CrudFormView.as_view(), name="crud_editar"),    # editar
    path("m/<slug:slug>/<int:pk>/eliminar/", views.CrudDeleteView.as_view(), name="crud_eliminar"),  # eliminar
]
