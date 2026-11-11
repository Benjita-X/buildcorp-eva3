"""
Gestión de usuarios con templates propios (separada del Django Admin).
  - Login / logout / cambio de contraseña propia: cualquier usuario.
  - Listar, crear, editar y resetear clave de usuarios: solo el rol Administrador.
"""
from django.contrib import messages
from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import PermissionRequiredMixin
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, UpdateView

from .forms import ClaveForm, MiClaveForm, UsuarioCrearForm, UsuarioEditarForm


class LoginView(auth_views.LoginView):
    template_name = "usuarios/login.html"
    redirect_authenticated_user = True


class CambiarMiClaveView(auth_views.PasswordChangeView):
    form_class = MiClaveForm
    template_name = "usuarios/clave.html"
    success_url = reverse_lazy("dashboard")

    def form_valid(self, form):
        messages.success(self.request, "Tu contraseña fue actualizada.")
        return super().form_valid(form)


class UsuarioListView(PermissionRequiredMixin, ListView):
    permission_required = "auth.view_user"
    template_name = "usuarios/lista.html"
    context_object_name = "usuarios"
    paginate_by = 20

    def get_queryset(self):
        qs = User.objects.prefetch_related("groups").order_by("username")
        q = self.request.GET.get("q", "").strip()
        if q:
            qs = qs.filter(Q(username__icontains=q) | Q(first_name__icontains=q) | Q(last_name__icontains=q))
        return qs


class ProtegerSuperusuarioMixin:
    """Un administrador normal no puede modificar al superusuario."""

    def get_object(self, queryset=None):
        usuario = super().get_object(queryset)
        if usuario.is_superuser and not self.request.user.is_superuser:
            raise PermissionDenied
        return usuario


class UsuarioCreateView(PermissionRequiredMixin, CreateView):
    permission_required = "auth.add_user"
    form_class = UsuarioCrearForm
    template_name = "usuarios/form.html"
    success_url = reverse_lazy("usuarios:lista")

    def form_valid(self, form):
        messages.success(self.request, f"Usuario «{form.cleaned_data['username']}» creado.")
        return super().form_valid(form)


class UsuarioUpdateView(PermissionRequiredMixin, ProtegerSuperusuarioMixin, UpdateView):
    permission_required = "auth.change_user"
    model = User
    form_class = UsuarioEditarForm
    template_name = "usuarios/form.html"
    success_url = reverse_lazy("usuarios:lista")

    def form_valid(self, form):
        if form.instance == self.request.user and not form.cleaned_data["is_active"]:
            form.add_error("is_active", "No puedes desactivar tu propia cuenta.")
            return self.form_invalid(form)
        messages.success(self.request, f"Usuario «{form.instance.username}» actualizado.")
        return super().form_valid(form)


class UsuarioClaveView(PermissionRequiredMixin, FormView):
    """El administrador asigna una contraseña nueva a otro usuario."""

    permission_required = "auth.change_user"
    form_class = ClaveForm
    template_name = "usuarios/clave.html"

    def dispatch(self, request, *args, **kwargs):
        self.usuario = get_object_or_404(User, pk=kwargs["pk"])
        if self.usuario.is_superuser and not request.user.is_superuser:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "user": self.usuario}

    def get_context_data(self, **kwargs):
        return super().get_context_data(usuario=self.usuario, **kwargs)

    def form_valid(self, form):
        form.save()
        messages.success(self.request, f"Contraseña de «{self.usuario.username}» actualizada.")
        return redirect("usuarios:lista")
