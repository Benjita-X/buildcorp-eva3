from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from core.crud import estilizar
from parametros.models import EstadoActivo

from .models import Activo, Bodega


class TrasladoForm(forms.Form):
    bodega = forms.ModelChoiceField(Bodega.objects.filter(vigente=True), label="Bodega de destino")
    motivo = forms.CharField(max_length=200)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)


class BajaForm(forms.Form):
    motivo = forms.CharField(max_length=200, label="Motivo de la baja")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        estilizar(self)


@permission_required("inventario.view_activo", raise_exception=True)
def activo_detalle(request, pk):
    """Hoja de vida del activo: datos, planes de mantenimiento, préstamos, OTs y trazabilidad."""
    activo = get_object_or_404(Activo.objects.select_related("categoria", "marca", "estado", "bodega"), pk=pk)
    return render(request, "inventario/activo_detalle.html", {
        "a": activo,
        "movimientos": activo.movimientos.select_related(
            "estado_anterior", "estado_nuevo", "bodega_origen", "bodega_destino", "usuario"
        )[:50],
        "prestamos": activo.detalles_prestamo.select_related("prestamo__contratista", "prestamo__estado", "condicion")
        .order_by("-prestamo__fecha_entrega")[:20],
        "planes": activo.planes_mantenimiento.select_related("tipo"),
        "ots": activo.mantenimientos.select_related("tipo", "estado")[:20],
        "traslado_form": TrasladoForm(initial={"bodega": activo.bodega}),
        "baja_form": BajaForm(),
    })


@require_POST
@permission_required("inventario.change_activo", raise_exception=True)
def activo_trasladar(request, pk):
    activo = get_object_or_404(Activo, pk=pk)
    form = TrasladoForm(request.POST)
    if activo.estado.codigo != EstadoActivo.DISPONIBLE:
        messages.error(request, "Solo se pueden trasladar activos disponibles (no prestados ni en mantención).")
    elif form.is_valid():
        destino = form.cleaned_data["bodega"]
        if destino == activo.bodega:
            messages.warning(request, "El activo ya está en esa bodega.")
        else:
            activo.bodega = destino
            activo._usuario, activo._motivo = request.user, f"Traslado: {form.cleaned_data['motivo']}"
            activo.save()
            messages.success(request, f"{activo.codigo} trasladado a {destino}.")
    else:
        messages.error(request, "Datos de traslado inválidos.")
    return redirect(activo)


@require_POST
@permission_required("inventario.change_activo", raise_exception=True)
def activo_baja(request, pk):
    activo = get_object_or_404(Activo, pk=pk)
    form = BajaForm(request.POST)
    if activo.estado.codigo == EstadoActivo.EN_USO:
        messages.error(request, "No se puede dar de baja un activo prestado. Registre primero la devolución.")
    elif activo.estado.codigo == EstadoActivo.BAJA:
        messages.info(request, "El activo ya está dado de baja.")
    elif form.is_valid():
        activo.cambiar_estado(EstadoActivo.BAJA, request.user, f"Dado de baja: {form.cleaned_data['motivo']}")
        messages.success(request, f"{activo.codigo} dado de baja.")
    return redirect(activo)
