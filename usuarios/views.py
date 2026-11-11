"""
Gestión de usuarios con templates propios (separada del Django Admin).
  - Login / logout / cambio de contraseña propia: cualquier usuario.
  - Listar, crear, editar y resetear clave de usuarios: solo el rol Administrador.
"""
# Aquí se usan VISTAS BASADAS EN CLASES (CBV): Django ya trae hecho el
# comportamiento de listar (ListView), crear (CreateView) y editar (UpdateView);
# solo se configura el modelo, el formulario, el template y el permiso.
from django.contrib import messages
from django.contrib.auth import views as auth_views        # vistas de login/logout de Django
from django.contrib.auth.mixins import PermissionRequiredMixin  # exige un permiso para entrar
from django.contrib.auth.models import User                 # el modelo de usuarios de Django
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, UpdateView

from .forms import ClaveForm, MiClaveForm, UsuarioCrearForm, UsuarioEditarForm


# Login: usa la vista de Django con nuestro propio template
class LoginView(auth_views.LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True  # si ya inició sesión, lo manda al dashboard


# Cambiar MI contraseña (cualquier usuario, pidiendo la contraseña actual)
class CambiarMiClaveView(auth_views.PasswordChangeView):
    form_class = MiClaveForm
    template_name = "usuarios/clave.html"
    success_url = reverse_lazy("dashboard")  # a dónde va después de guardar

    def form_valid(self, form):
        messages.success(self.request, "Tu contraseña fue actualizada.")
        return super().form_valid(form)


# LISTAR usuarios (solo quien tenga el permiso "ver usuarios": el Administrador)
class UsuarioListView(PermissionRequiredMixin, ListView):
    permission_required = "auth.view_user"
    template_name = "usuarios/lista.html"
    context_object_name = "usuarios"  # nombre de la lista dentro del template
    paginate_by = 20                  # 20 usuarios por página

    # Consulta de usuarios, con buscador por usuario, nombre o apellido
    def get_queryset(self):
        qs = User.objects.prefetch_related("groups").order_by("username")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs


# Protección: un administrador normal no puede modificar al superusuario
class ProtegerSuperusuarioMixin:
    """Un administrador normal no puede modificar al superusuario."""

    def get_object(self, queryset=None):
        usuario = super().get_object(queryset)
        if usuario.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied
        return usuario


# CREAR usuario con su rol (exige el permiso "agregar usuarios")
class UsuarioCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "auth.add_user"
    form_class = UsuarioCrearForm
    template_name = "usuarios/form.html"
    success_url = reverse_lazy("usuarios:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Usuario «{form.cleaned_data['username']}» creado.")
        return super().form_valid(form)


# EDITAR usuario: nombre, correo, rol y si está activo (exige "cambiar usuarios")
class UsuarioUpdateView(PermissionRequiredMixin, ProtegerSuperusuarioMixin, UpdateView):
    permission_required = "auth.change_user"
    model = User
    form_class = UsuarioEditarForm
    template_name = "usuarios/form.html"
    success_url = reverse_lazy("usuarios:lista")

    def form_valid(self, form):
        # Nadie puede desactivar su propia cuenta (para no quedar fuera del sistema)
        if form.instance == self.request.user and not form.cleaned_data["is_active"]:
            form.add_error("is_active", "No puedes desactivar tu propia cuenta.")
            return self.form_invalid(form)
        messages.success(self.request, f"Usuario «{form.instance.username}» actualizado.")
        return super().form_valid(form)


# El administrador le asigna una contraseña nueva a otro usuario
class UsuarioClaveView(PermissionRequiredMixin, FormView):
    """El administrador asigna una contraseña nueva a otro usuario."""

    permission_required = "auth.change_user"
    form_class = ClaveForm
    template_name = "usuarios/clave.html"

    # Busca el usuario de la URL; si es superusuario y quien entra no lo es, lo bloquea
    def dispatch(self, request, *args, **kwargs):
        self.usuario = get_object_or_404(User, pk=kwargs["pk"])
        if self.usuario.is_superuser and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    # Le pasa al formulario el usuario al que se le cambia la clave
    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.usuario}

    def get_context_data(self, **kwargs):
        return super().get_context_data(usuario=self.usuario, **kwargs)

    def form_valid(self, form):
        form.save()  # guarda la contraseña nueva (encriptada)
        messages.success(self.request, f"Contraseña de «{self.usuario.username}» actualizada.")
        return redirect("usuarios:lista")
