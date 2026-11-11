from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("mantenedores/", views.parametrizacion, name="mantenedores"),
    # Mantenedores genéricos (uno por tabla), todos con los mismos templates
    path("m/<slug:slug>/", views.CrudListView.as_view(), name="crud_lista"),
    path("m/<slug:slug>/nuevo/", views.CrudFormView.as_view(), name="crud_crear"),
    path("m/<slug:slug>/<int:pk>/", views.CrudDetailView.as_view(), name="crud_detalle"),
    path("m/<slug:slug>/<int:pk>/editar/", views.CrudFormView.as_view(), name="crud_editar"),
    path("m/<slug:slug>/<int:pk>/eliminar/", views.CrudDeleteView.as_view(), name="crud_eliminar"),
]
