# =============================================================================
# Formularios de la app usuarios (crear, editar y cambiar contraseña).
# =============================================================================
from django import forms
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import Group, User

from core.crud import estilizar  # agrega el estilo Bootstrap a los campos


# Campo "Rol": una lista con los Grupos de Django (Administrador, Bodeguero, ...)
class RolField(forms.ModelChoiceField):
    """El rol del usuario = un Grupo de Django (Administrador, Bodeguero, ...)."""

    def __init__(self, **kwargs):
        super().__init__(Group.objects.order_by("name"), label="Rol", **kwargs)


# Formulario para CREAR un usuario. UserCreationForm (de Django) ya trae
# usuario + contraseña + repetir contraseña, y valida que coincidan.
class UsuarioCrearForm(UserCreationForm):
    rol = RolField()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Nombre, apellido y correo obligatorios
        for campo in ("first_name", "last_name", "email"):
            self.fields[campo].required = True
        estilizar(self)

    # Al guardar, asigna el rol elegido (el grupo) al usuario
    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set([self.cleaned_data["rol"]])
        return usuario


# Formulario para EDITAR un usuario (sin contraseña)
class UsuarioEditarForm(forms.ModelForm):
    rol = RolField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]
        labels = {"is_active": "Activo (puede iniciar sesión)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].initial = self.instance.groups.first()  # muestra el rol actual
        estilizar(self)

    # Al guardar, actualiza el rol del usuario
    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set([self.cleaned_data["rol"]])
        return usuario


# El administrador pone una contraseña nueva (no pide la anterior)
class ClaveForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)


# El propio usuario cambia su contraseña (pide la contraseña actual)
class MiClaveForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)
