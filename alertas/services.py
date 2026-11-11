"""
Reglas automáticas de alertas:
  1. Morosidad: préstamo abierto cuya fecha comprometida + días de gracia ya pasó
     -> el préstamo pasa a ATRASADO y se genera una alerta de MOROSIDAD.
  2. Bloqueo automático: si un contratista acumula >= MAX_PRESTAMOS_MOROSOS
     préstamos morosos, se bloquea (no puede pedir más herramientas).
     Se puede desactivar con el parámetro BLOQUEO_AUTOMATICO = 0 (por defecto 1 = Sí);
     el bloqueo manual siempre está disponible en la ficha del contratista.
  3. Desbloqueo automático: si el bloqueo fue automático y ya no tiene morosos.
  4. Préstamos por vencer y mantenciones vencidas / por vencer.

Se ejecuta al abrir el dashboard o el listado de alertas.
"""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from contratistas.models import Contratista
from parametros.models import EstadoPrestamo, ParametroSistema, TipoAlerta

from .models import Alerta


# Crea una alerta evitando duplicados
def crear_alerta(codigo_tipo, mensaje, una_vez=False, **relaciones):
    """Crea la alerta si no existe una igual sin resolver (evita duplicados).
    Con una_vez=True tampoco la vuelve a crear si el usuario ya la resolvió
    (se usa en las alertas de un préstamo: morosidad y por vencer)."""
    tipo = TipoAlerta.por_codigo(codigo_tipo)
    existentes = Alerta.objects.filter(tipo=tipo, **relaciones)
    if not una_vez:
        existentes = existentes.filter(resuelta=False)
    if existentes.exists():
        return None
    return Alerta.objects.create(tipo=tipo, mensaje=mensaje, **relaciones)


# Marca como resueltas las alertas que cumplan el filtro
def resolver_alertas(usuario=None, **filtros):
    for alerta in Alerta.objects.filter(resuelta=False, **filtros):
        alerta.resolver(usuario)


# Préstamos sin devolver cuya fecha comprometida + días de gracia ya pasó
def prestamos_morosos():
    from prestamos.models import Prestamo

    dias_gracia = ParametroSistema.get_int(ParametroSistema.DIAS_GRACIA, 0)
    limite = timezone.localdate() - timedelta(days=dias_gracia)
    return Prestamo.objects.filter(fecha_devolucion__isnull=True, fecha_compromiso__lt=limite)


# BLOQUEO AUTOMÁTICO: si el contratista llega al máximo de préstamos morosos
# y el parámetro BLOQUEO_AUTOMATICO está en 1, se bloquea. Si ya no tiene
# morosos y el bloqueo fue automático, se desbloquea solo.
def reevaluar_bloqueo(contratista):
    maximo = max(1, ParametroSistema.get_int(ParametroSistema.MAX_MOROSOS, 1))
    morosos = prestamos_morosos().filter(contratista=contratista).count()
    automatico = ParametroSistema.get_int(ParametroSistema.BLOQUEO_AUTO, 1) == 1  # 1 = Sí (por defecto)
    if automatico and morosos >= maximo and not contratista.bloqueado:
        contratista.bloquear(
            f"Bloqueo automático: {morosos} préstamo(s) con devolución atrasada.", automatico=True
        )
        crear_alerta(
            TipoAlerta.BLOQUEO,
            f"{contratista.razon_social} fue bloqueado automáticamente por morosidad ({morosos} préstamo(s)).",
            contratista=contratista,
        )
        return "bloqueado"
    if morosos == 0 and contratista.bloqueado and contratista.bloqueo_automatico:
        contratista.desbloquear()
        resolver_alertas(contratista=contratista, tipo__codigo=TipoAlerta.BLOQUEO)
        return "desbloqueado"
    return None


# Marca los préstamos morosos como "Atrasado", crea sus alertas y revisa bloqueos
@transaction.atomic
def revisar_morosidad():
    atrasado = EstadoPrestamo.por_codigo(EstadoPrestamo.ATRASADO)
    resumen = {"morosos": 0, "bloqueados": 0, "desbloqueados": 0, "alertas": 0}
    contratistas = set()
    for p in prestamos_morosos().select_related("contratista", "obra"):
        resumen["morosos"] += 1
        if p.estado_id != atrasado.pk:
            p.estado = atrasado
            p.save(update_fields=["estado"])
        if crear_alerta(
            TipoAlerta.MOROSIDAD,
            f"Préstamo {p.folio} de {p.contratista.razon_social} atrasado {p.dias_atraso} día(s) (obra {p.obra.codigo}).",
            prestamo=p, contratista=p.contratista, una_vez=True,
        ):
            resumen["alertas"] += 1
        contratistas.add(p.contratista_id)

    # También revisamos los bloqueados automáticos que quizá ya regularizaron
    contratistas |= set(Contratista.objects.filter(bloqueado=True, bloqueo_automatico=True).values_list("pk", flat=True))
    for c in Contratista.objects.filter(pk__in=contratistas):
        resultado = reevaluar_bloqueo(c)
        if resultado:
            resumen[resultado + "s"] += 1
    return resumen


# Alerta de préstamos que vencen pronto
def revisar_por_vencer():
    from prestamos.models import Prestamo

    dias = ParametroSistema.get_int(ParametroSistema.DIAS_AVISO_VENC, 2)
    hoy = timezone.localdate()
    n = 0
    for p in Prestamo.objects.filter(
        fecha_devolucion__isnull=True, fecha_compromiso__gte=hoy, fecha_compromiso__lte=hoy + timedelta(days=dias)
    ).select_related("contratista"):
        if crear_alerta(
            TipoAlerta.POR_VENCER,
            f"Préstamo {p.folio} de {p.contratista.razon_social} vence el {p.fecha_compromiso:%d-%m-%Y}.",
            prestamo=p, contratista=p.contratista, una_vez=True,
        ):
            n += 1
    return n


# Ejecuta todas las revisiones (se llama al abrir el dashboard o las alertas)
def ejecutar_revisiones():
    from mantenimiento.services import revisar_mantenciones

    resumen = revisar_morosidad()
    resumen["por_vencer"] = revisar_por_vencer()
    resumen.update(revisar_mantenciones())
    return resumen
