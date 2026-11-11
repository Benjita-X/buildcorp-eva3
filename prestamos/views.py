from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from . import services
from .forms import DevolucionForm, PrestamoForm
from .models import Prestamo


@permission_required("prestamos.add_prestamo", raise_exception=True)
def nuevo(request):
    form = PrestamoForm(request.POST or None, initial=request.GET.dict() or None)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            prestamo = services.registrar_prestamo(
                contratista=d["contratista"], responsable=d["responsable"], obra=d["obra"],
                fecha_compromiso=d["fecha_compromiso"], activos=list(d["activos"]), firma=d["firma"],
                usuario=request.user, observaciones=d["observaciones"],
            )
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
        else:
            messages.success(request, f"Préstamo {prestamo.folio} registrado. {len(d['activos'])} herramienta(s) entregadas.")
            return redirect(prestamo)
    elif request.method == "POST":
        messages.error(request, "Revise los errores del formulario.")
    return render(request, "prestamos/nuevo.html", {"form": form})


@permission_required("prestamos.view_prestamo", raise_exception=True)
def detalle(request, pk):
    prestamo = get_object_or_404(
        Prestamo.objects.select_related("contratista", "responsable", "obra", "estado", "usuario_entrega"), pk=pk
    )
    return render(request, "prestamos/detalle.html", {
        "p": prestamo, "detalles": prestamo.detalles.select_related("activo", "bodega_origen", "condicion"),
    })


@permission_required("prestamos.change_prestamo", raise_exception=True)
def devolver(request, pk):
    prestamo = get_object_or_404(Prestamo, pk=pk)
    if not prestamo.abierto:
        messages.info(request, "Este préstamo ya fue devuelto.")
        return redirect(prestamo)
    form = DevolucionForm(request.POST or None, prestamo=prestamo)
    if request.method == "POST" and form.is_valid():
        d = form.cleaned_data
        try:
            services.registrar_devolucion(
                prestamo=prestamo, devoluciones=form.devoluciones(), bodega_recepcion=d["bodega_recepcion"],
                firma=d["firma"], devuelto_por=d["devuelto_por"], usuario=request.user,
                observaciones=d["observaciones"],
            )
        except ValidationError as e:
            for msg in e.messages:
                messages.error(request, msg)
        else:
            prestamo.refresh_from_db()
            messages.success(request, f"Devolución registrada. Total a cobrar: $ {prestamo.total:,.0f}".replace(",", "."))
            return redirect(prestamo)
    return render(request, "prestamos/devolver.html", {"form": form, "p": prestamo})
