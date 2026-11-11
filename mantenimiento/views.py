# Vistas de órdenes de trabajo: ver detalle, iniciar, completar y cancelar
from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Mantenimiento


@permission_required("mantenimiento.view_mantenimiento", raise_exception=True)
# Detalle de la OT (con los botones según su estado)
def detalle(request, pk):
    ot = get_object_or_404(Mantenimiento.objects.select_related("activo", "tipo", "estado", "plan", "creado_por"), pk=pk)
    return render(request, "mantenimiento/detalle.html", {"ot": ot})


# Ejecuta una acción del servicio y muestra el mensaje de éxito o de error
def _accion(request, pk, fn, ok):
    ot = get_object_or_404(Mantenimiento, pk=pk)
    try:
        fn(ot)
    except ValidationError as e:
        for msg in e.messages:
            messages.error(request, msg)
    else:
        messages.success(request, ok.format(ot=ot))
    return redirect(ot)


@require_POST
@permission_required("mantenimiento.change_mantenimiento", raise_exception=True)
# Botón "Iniciar"
def iniciar(request, pk):
    return _accion(request, pk, lambda ot: services.iniciar(ot, request.user), "{ot.folio} en proceso. Activo en mantención.")


@require_POST
@permission_required("mantenimiento.change_mantenimiento", raise_exception=True)
# Botón "Completar" (exige describir el trabajo realizado)
def completar(request, pk):
    trabajo = request.POST.get("trabajo_realizado", "").strip()
    if not trabajo:
        messages.error(request, "Debe describir el trabajo realizado.")
        return redirect("mantenimiento:detalle", pk)
    return _accion(
        request, pk,
        lambda ot: services.completar(ot, trabajo, request.POST.get("tecnico", "").strip(), request.user),
        "{ot.folio} completada. El activo vuelve a estar disponible.",
    )


@require_POST
@permission_required("mantenimiento.change_mantenimiento", raise_exception=True)
# Botón "Cancelar OT"
def cancelar(request, pk):
    return _accion(request, pk, lambda ot: services.cancelar(ot, request.user), "{ot.folio} cancelada.")
