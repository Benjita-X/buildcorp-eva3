from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from alertas.services import crear_alerta, resolver_alertas
from parametros.models import TipoAlerta

from .models import Contratista


@permission_required("contratistas.view_contratista", raise_exception=True)
def detalle(request, pk):
    c = get_object_or_404(Contratista.objects.select_related("comuna__ciudad__region"), pk=pk)
    prestamos = list(c.prestamos.select_related("obra", "estado").prefetch_related("detalles"))
    abiertos = [p for p in prestamos if p.abierto]
    return render(request, "contratistas/detalle.html", {
        "c": c,
        "responsables": c.responsables.select_related("cargo"),
        "prestamos": prestamos[:30],
        "abiertos": len(abiertos),
        "morosos": sum(1 for p in abiertos if p.vencido),
        "deuda_abierta": sum(p.total for p in abiertos),
        "alertas": c.alertas.filter(resuelta=False).select_related("tipo"),
    })


@require_POST
@permission_required("contratistas.change_contratista", raise_exception=True)
def bloquear(request, pk):
    c = get_object_or_404(Contratista, pk=pk)
    motivo = request.POST.get("motivo", "").strip() or "Bloqueo manual"
    c.bloquear(f"{motivo} (por {request.user.username})", automatico=False)
    crear_alerta(TipoAlerta.BLOQUEO, f"{c.razon_social} bloqueado manualmente: {motivo}", contratista=c)
    messages.warning(request, f"{c.razon_social} quedó bloqueado.")
    return redirect(c)


@require_POST
@permission_required("contratistas.change_contratista", raise_exception=True)
def desbloquear(request, pk):
    c = get_object_or_404(Contratista, pk=pk)
    c.desbloquear()
    resolver_alertas(request.user, contratista=c, tipo__codigo=TipoAlerta.BLOQUEO)
    messages.success(request, f"{c.razon_social} fue desbloqueado. "
                     "Si mantiene préstamos morosos volverá a bloquearse en la próxima revisión.")
    return redirect(c)
