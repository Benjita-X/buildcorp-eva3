from django import forms
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.models import Group, User

from core.crud import estilizar


class RolField(forms.ModelChoiceField):
    """El rol del usuario = un Grupo de Django (Administrador, Bodeguero, ...)."""

    def __init__(self, **kwargs):
        super().__init__(Group.objects.order_by("name"), label="Rol", **kwargs)


class UsuarioCrearForm(UserCreationForm):
    rol = RolField()

    class Meta:
        model = User
        fields = ["username", "first_name", "last_name", "email"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in ("first_name", "last_name", "email"):
            self.fields[campo].required = True
        estilizar(self)

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set([self.cleaned_data["rol"]])
        return usuario


class UsuarioEditarForm(forms.ModelForm):
    rol = RolField()

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "is_active"]
        labels = {"is_active": "Activo (puede iniciar sesión)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["rol"].initial = self.instance.groups.first()
        estilizar(self)

    def save(self, commit=True):
        usuario = super().save(commit=commit)
        if commit:
            usuario.groups.set([self.cleaned_data["rol"]])
        return usuario


class ClaveForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)


class MiClaveForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)
