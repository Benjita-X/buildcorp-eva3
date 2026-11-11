"""
Motor de MANTENEDORES basado en templates.

Cada tabla del sistema se registra una vez (en el `mantenedores.py` de su app)
con su configuración: columnas, búsqueda, filtros, campos del formulario, etc.
A partir de ese registro se generan automáticamente sus pantallas CRUD
(listar / ver / crear / editar / eliminar) usando los mismos templates HTML:

    templates/core/crud_list.html
    templates/core/crud_form.html
    templates/core/crud_detail.html
    templates/core/crud_confirm_delete.html

Las URLs quedan como /m/<slug>/, /m/<slug>/nuevo/, /m/<slug>/<pk>/editar/ ...
y cada acción respeta los permisos de Django (view/add/change/delete).
"""
from dataclasses import dataclass, field
from typing import Callable, Optional

from django import forms
from django.db import models

REGISTRO: dict = {}


@dataclass
class Mantenedor:
    model: type
    slug: str
    grupo: str
    icono: str = "bi-table"
    columnas: list = field(default_factory=list)       # nombres de campo o propiedades
    busqueda: list = field(default_factory=list)       # campos para icontains (admite __)
    filtros: list = field(default_factory=list)        # FK / booleanos / choices
    campos: object = "__all__"                         # campos del formulario
    form_class: Optional[type] = None
    titulo: Optional[str] = None
    orden: int = 100
    permite_crear: bool = True
    permite_editar: bool = True
    permite_eliminar: bool = True
    url_crear: Optional[str] = None                    # nombre de URL para un flujo propio
    url_detalle: Optional[str] = None                  # nombre de URL para un detalle propio
    antes_de_guardar: Optional[Callable] = None        # fn(obj, request, creando)
    queryset: Optional[Callable] = None                # fn(request) -> QuerySet
    ayuda: str = ""
    acciones: Optional[Callable] = None                # fn(obj, user) -> [botones extra por fila]

    def __post_init__(self):
        opts = self.model._meta
        self.titulo = self.titulo or opts.verbose_name_plural.capitalize()
        self.titulo_singular = opts.verbose_name.capitalize()
        self.app_label, self.model_name = opts.app_label, opts.model_name
        if not self.columnas:
            self.columnas = [f.name for f in opts.fields if f.name != "id"][:6]

    def perm(self, accion):
        return f"{self.app_label}.{accion}_{self.model_name}"

    def get_queryset(self, request=None):
        if self.queryset:
            return self.queryset(request)
        qs = self.model._default_manager.all()
        relacionados = [
            c for c in self.columnas
            if isinstance(self._campo(c), (models.ForeignKey, models.OneToOneField))
        ]
        return qs.select_related(*relacionados) if relacionados else qs

    def _campo(self, nombre):
        try:
            return self.model._meta.get_field(nombre)
        except Exception:
            return None

    def etiqueta(self, nombre):
        campo = self._campo(nombre)
        if campo is not None:
            return str(campo.verbose_name).capitalize()
        attr = getattr(self.model, nombre, None)
        corto = getattr(attr, "short_description", None) or getattr(getattr(attr, "fget", None), "short_description", None)
        return corto or nombre.replace("_", " ").capitalize()

    def get_form_class(self):
        if self.form_class:
            return self.form_class
        return forms.modelform_factory(
            self.model, form=FormularioBootstrap, fields=self.campos,
            formfield_callback=_formfield_callback,
        )


def registrar(m: Mantenedor):
    if m.slug in REGISTRO:
        raise ValueError(f"Mantenedor duplicado: {m.slug}")
    REGISTRO[m.slug] = m
    return m


# --------------------------------------------------------------------------
# Formularios con estilo Bootstrap
# --------------------------------------------------------------------------
def _formfield_callback(campo, **kwargs):
    if isinstance(campo, models.DateTimeField):
        kwargs["widget"] = forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M")
    elif isinstance(campo, models.DateField):
        kwargs["widget"] = forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")
    elif isinstance(campo, models.TextField):
        kwargs["widget"] = forms.Textarea(attrs={"rows": 3})
    return campo.formfield(**kwargs)


def estilizar(form):
    for nombre, campo in form.fields.items():
        w = campo.widget
        if isinstance(w, (forms.CheckboxInput,)):
            w.attrs.setdefault("class", "form-check-input")
        elif isinstance(w, (forms.Select, forms.SelectMultiple)):
            w.attrs.setdefault("class", "form-select")
        elif isinstance(w, forms.CheckboxSelectMultiple):
            pass
        else:
            w.attrs.setdefault("class", "form-control")
        # Las FK solo muestran registros vigentes (más el valor actual al editar)
        if isinstance(campo, forms.ModelChoiceField) and hasattr(campo.queryset.model, "vigente"):
            actual = form.initial.get(nombre)
            filtro = models.Q(vigente=True)
            if actual:
                filtro |= models.Q(pk=getattr(actual, "pk", actual))
            campo.queryset = campo.queryset.filter(filtro)


class FormularioBootstrap(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)
        # Los códigos de los parámetros de sistema no se pueden cambiar
        if getattr(self.instance, "es_sistema", False):
            for nombre in ("codigo", "clave"):
                if nombre in self.fields:
                    self.fields[nombre].disabled = True
                    self.fields[nombre].help_text = "Código de sistema (no editable)."
