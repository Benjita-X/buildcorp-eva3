from django.contrib import messages
from django.contrib.auth.decorators import permission_required
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from parametros.models import TipoAlerta

from .models import Alerta
from .services import ejecutar_revisiones


@permission_required("alertas.view_alerta", raise_exception=True)
def lista(request):
    ejecutar_revisiones()
    ver = request.GET.get("ver", "pendientes")
    qs = Alerta.objects.select_related("tipo", "contratista", "prestamo", "activo", "resuelta_por")
    qs = qs.filter(resuelta=(ver == "resueltas"))
    tipo = request.GET.get("tipo", "")
    if tipo:
        qs = qs.filter(tipo__codigo=tipo)
    return render(request, "alertas/lista.html", {
        "pagina": Paginator(qs, 20).get_page(request.GET.get("page")),
        "ver": ver, "tipo": tipo, "tipos": TipoAlerta.objects.filter(vigente=True),
    })


@require_POST
@permission_required("alertas.change_alerta", raise_exception=True)
def resolver(request, pk):
    alerta = get_object_or_404(Alerta, pk=pk)
    alerta.resolver(request.user)
    messages.success(request, "Alerta marcada como resuelta.")
    return redirect(request.POST.get("next") or "alertas:lista")


@require_POST
@permission_required("alertas.change_alerta", raise_exception=True)
def revisar(request):
    r = ejecutar_revisiones()
    messages.info(
        request,
        f"Revisión ejecutada: {r['morosos']} préstamo(s) moroso(s), {r['bloqueados']} bloqueo(s) nuevo(s), "
        f"{r['desbloqueados']} desbloqueo(s), {r['ot_generadas']} OT(s) preventivas generadas.",
    )
    return redirect("alertas:lista")
