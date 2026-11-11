"""Lógica de mantenimiento preventivo/correctivo."""
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from parametros.models import EstadoActivo, EstadoMantenimiento, TipoAlerta, TipoMantenimiento

from .models import Mantenimiento, PlanMantenimiento

ESTADOS_ABIERTOS = (EstadoMantenimiento.PROGRAMADA, EstadoMantenimiento.EN_PROCESO)


def ot_abierta(activo, plan=None):
    qs = Mantenimiento.objects.filter(activo=activo, estado__codigo__in=ESTADOS_ABIERTOS)
    if plan is not None:
        qs = qs.filter(plan=plan)
    return qs.first()


def programar_desde_plan(plan, usuario=None):
    """Crea la OT preventiva de un plan vencido (si no tiene una abierta)."""
    if ot_abierta(plan.activo, plan):
        return None
    return Mantenimiento.objects.create(
        activo=plan.activo, plan=plan, tipo=plan.tipo,
        estado=EstadoMantenimiento.por_codigo(EstadoMantenimiento.PROGRAMADA),
        fecha_programada=timezone.localdate(),
        descripcion=f"[Automática] {plan.descripcion}", creado_por=usuario,
    )


def crear_correctiva(activo, motivo, usuario=None):
    return Mantenimiento.objects.create(
        activo=activo, tipo=TipoMantenimiento.por_codigo(TipoMantenimiento.CORRECTIVO),
        estado=EstadoMantenimiento.por_codigo(EstadoMantenimiento.PROGRAMADA),
        fecha_programada=timezone.localdate(), descripcion=motivo, creado_por=usuario,
    )


def revisar_mantenciones():
    """Genera OTs para planes vencidos y alertas para vencidos / por vencer."""
    from alertas.services import crear_alerta

    resumen = {"ot_generadas": 0, "alertas_mantencion": 0}
    for plan in PlanMantenimiento.objects.filter(vigente=True).select_related("activo", "activo__estado"):
        if plan.activo.estado.codigo == EstadoActivo.BAJA:
            continue
        if plan.esta_vencido:
            if programar_desde_plan(plan):
                resumen["ot_generadas"] += 1
            msg = f"Mantención vencida: {plan.activo} · {plan.descripcion}."
        elif plan.por_vencer:
            msg = f"Mantención próxima: {plan.activo} · {plan.descripcion}."
        else:
            continue
        if crear_alerta(TipoAlerta.MANTENCION, msg, activo=plan.activo):
            resumen["alertas_mantencion"] += 1
    return resumen


@transaction.atomic
def iniciar(ot, usuario=None):
    if ot.estado.codigo != EstadoMantenimiento.PROGRAMADA:
        raise ValidationError("Solo se pueden iniciar órdenes en estado Programada.")
    if ot.activo.estado.codigo == EstadoActivo.EN_USO:
        raise ValidationError("El activo está prestado en obra. Debe devolverse antes de iniciar la mantención.")
    ot.estado = EstadoMantenimiento.por_codigo(EstadoMantenimiento.EN_PROCESO)
    ot.fecha_inicio = timezone.now()
    ot.save()
    if ot.activo.estado.codigo != EstadoActivo.MANTENCION:
        ot.activo.cambiar_estado(EstadoActivo.MANTENCION, usuario, f"Ingreso a mantención ({ot.folio})")


@transaction.atomic
def completar(ot, trabajo_realizado, costo, tecnico="", usuario=None):
    from alertas.services import resolver_alertas

    if ot.estado.codigo != EstadoMantenimiento.EN_PROCESO:
        raise ValidationError("Solo se pueden completar órdenes en proceso.")
    ot.estado = EstadoMantenimiento.por_codigo(EstadoMantenimiento.COMPLETADA)
    ot.fecha_termino = timezone.now()
    ot.horas_activo = ot.activo.horas_uso
    ot.trabajo_realizado = trabajo_realizado
    ot.costo = costo or 0
    if tecnico:
        ot.tecnico = tecnico
    ot.save()
    # Reinicia el contador de todos los planes vigentes del activo de ese tipo (o el plan de la OT)
    planes = [ot.plan] if ot.plan else list(ot.activo.planes_mantenimiento.filter(vigente=True, tipo=ot.tipo))
    for plan in planes:
        plan.ultima_fecha = timezone.localdate()
        plan.ultimas_horas = ot.activo.horas_uso
        plan.save()
    # Si no le quedan OTs abiertas, vuelve a estar disponible
    if not ot_abierta(ot.activo):
        ot.activo.cambiar_estado(EstadoActivo.DISPONIBLE, usuario, f"Mantención finalizada ({ot.folio})")
        resolver_alertas(usuario, activo=ot.activo, tipo__codigo=TipoAlerta.MANTENCION)


@transaction.atomic
def cancelar(ot, usuario=None):
    if not ot.abierta:
        raise ValidationError("La orden ya está cerrada.")
    estaba_en_proceso = ot.estado.codigo == EstadoMantenimiento.EN_PROCESO
    ot.estado = EstadoMantenimiento.por_codigo(EstadoMantenimiento.CANCELADA)
    ot.fecha_termino = timezone.now()
    ot.save()
    if estaba_en_proceso and not ot_abierta(ot.activo):
        ot.activo.cambiar_estado(EstadoActivo.DISPONIBLE, usuario, f"OT cancelada ({ot.folio})")
