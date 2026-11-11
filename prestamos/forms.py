from datetime import timedelta
from decimal import Decimal

from django import forms
from django.utils import timezone

from contratistas.models import Contratista, ResponsableObra
from core.crud import estilizar
from inventario.models import Activo, Bodega, Obra
from parametros.models import CondicionActivo


class PrestamoForm(forms.Form):
    contratista = forms.ModelChoiceField(
        Contratista.objects.filter(vigente=True, bloqueado=False),
        help_text="Los contratistas bloqueados por morosidad no aparecen.",
    )
    responsable = forms.ModelChoiceField(ResponsableObra.objects.filter(vigente=True), label="Responsable de obra (firma)")
    obra = forms.ModelChoiceField(Obra.objects.filter(vigente=True))
    fecha_compromiso = forms.DateField(
        label="Devolución comprometida", widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    activos = forms.ModelMultipleChoiceField(
        Activo.objects.none(), widget=forms.CheckboxSelectMultiple, label="Herramientas a entregar",
    )
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    firma = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["activos"].queryset = (
            Activo.objects.filter(estado__permite_prestamo=True)
            .select_related("categoria", "marca", "bodega", "estado").order_by("bodega__nombre", "codigo")
        )
        self.fields["fecha_compromiso"].initial = timezone.localdate() + timedelta(days=7)
        estilizar(self)


class DevolucionForm(forms.Form):
    bodega_recepcion = forms.ModelChoiceField(Bodega.objects.filter(vigente=True), label="Bodega que recibe")
    devuelto_por = forms.CharField(label="Nombre de quien devuelve", max_length=150)
    observaciones = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 2}))
    firma = forms.CharField(widget=forms.HiddenInput, required=False)

    def __init__(self, *args, prestamo, **kwargs):
        super().__init__(*args, **kwargs)
        self.prestamo = prestamo
        self.detalles = list(prestamo.detalles.select_related("activo", "bodega_origen"))
        buena = CondicionActivo.objects.filter(codigo=CondicionActivo.BUENA).first()
        for d in self.detalles:
            self.fields[f"horas_{d.pk}"] = forms.DecimalField(
                label="Horas de uso", min_value=Decimal("0"), max_digits=8, decimal_places=1, initial=0,
            )
            self.fields[f"condicion_{d.pk}"] = forms.ModelChoiceField(
                CondicionActivo.objects.filter(vigente=True), label="Condición", initial=buena,
            )
        if self.detalles:
            self.fields["bodega_recepcion"].initial = self.detalles[0].bodega_origen
        self.fields["devuelto_por"].initial = prestamo.responsable.nombre
        estilizar(self)

    def filas(self):
        return [(d, self[f"horas_{d.pk}"], self[f"condicion_{d.pk}"]) for d in self.detalles]

    def devoluciones(self):
        return {
            d.pk: (self.cleaned_data[f"horas_{d.pk}"], self.cleaned_data[f"condicion_{d.pk}"]) for d in self.detalles
        }
