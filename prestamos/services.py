"""
Reglas de negocio de préstamos (entrega y devolución de herramientas).

Entrega:
  - El contratista no puede estar bloqueado (morosidad).
  - El responsable debe pertenecer al contratista.
  - Cada activo debe estar en un estado que permita préstamo (Disponible)
    y no tener mantención preventiva vencida.
  - Se exige firma digital del responsable de obra.
  - Los activos pasan a "En Uso" y queda registro en su hoja de vida.

Devolución:
  - Se registran horas de uso y condición de cada herramienta.
  - Las horas se suman al activo (alimentan el mantenimiento por uso).
  - Condición que requiere mantención -> activo a "Mantenimiento" + OT correctiva.
  - Si no, vuelve a "Disponible" en la bodega de recepción.
  - Se exige firma digital; se resuelven las alertas y se reevalúa el bloqueo.
"""
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from parametros.models import EstadoActivo, EstadoPrestamo, TipoAlerta

from .models import DetallePrestamo, Prestamo

FIRMA_RE = re.compile(r"^data:image/png;base64,[A-Za-z0-9+/=]+$")


def validar_firma(firma):
    if not firma or not FIRMA_RE.match(firma) or len(firma) < 200:
        raise ValidationError("La firma digital es obligatoria.")


@transaction.atomic
def registrar_prestamo(*, contratista, responsable, obra, fecha_compromiso, activos, firma, usuario, observaciones=""):
    errores = []
    if contratista.bloqueado:
        errores.append(f"El contratista está BLOQUEADO: {contratista.motivo_bloqueo or 'sin motivo'}.")
    if not contratista.vigente:
        errores.append("El contratista no está vigente.")
    if responsable.contratista_id != contratista.pk:
        errores.append("El responsable de obra no pertenece al contratista seleccionado.")
    if fecha_compromiso < timezone.localdate():
        errores.append("La fecha de devolución comprometida no puede ser anterior a hoy.")
    if not activos:
        errores.append("Debe seleccionar al menos una herramienta.")
    for a in activos:
        a.refresh_from_db()
        if not a.estado.permite_prestamo:
            errores.append(f"{a} no está disponible (estado: {a.estado}).")
        elif a.mantencion_vencida():
            errores.append(f"{a} tiene la mantención preventiva vencida.")
    try:
        validar_firma(firma)
    except ValidationError as e:
        errores.extend(e.messages)
    if errores:
        raise ValidationError(errores)

    prestamo = Prestamo.objects.create(
        contratista=contratista, responsable=responsable, obra=obra,
        estado=EstadoPrestamo.por_codigo(EstadoPrestamo.VIGENTE),
        fecha_compromiso=fecha_compromiso, firma_entrega=firma,
        observaciones=observaciones, usuario_entrega=usuario,
    )
    for a in activos:
        DetallePrestamo.objects.create(prestamo=prestamo, activo=a, bodega_origen=a.bodega, tarifa_diaria=a.tarifa_diaria)
        a.cambiar_estado(
            EstadoActivo.EN_USO, usuario,
            f"Entregado en préstamo {prestamo.folio} a {contratista.razon_social} (obra {obra.codigo}), firma de {responsable.nombre}",
        )
    return prestamo


@transaction.atomic
def registrar_devolucion(*, prestamo, devoluciones, bodega_recepcion, firma, devuelto_por, usuario, observaciones=""):
    """devoluciones: dict {detalle_id: (horas_uso: Decimal, condicion: CondicionActivo)}"""
    from alertas.services import reevaluar_bloqueo, resolver_alertas
    from mantenimiento.services import crear_correctiva, revisar_mantenciones

    if not prestamo.abierto:
        raise ValidationError("Este préstamo ya fue devuelto.")
    validar_firma(firma)

    for det in prestamo.detalles.select_related("activo"):
        horas, condicion = devoluciones[det.pk]
        if horas < 0:
            raise ValidationError("Las horas de uso no pueden ser negativas.")
        det.horas_uso, det.condicion, det.devuelto = horas, condicion, True
        det.save()
        activo = det.activo
        activo.horas_uso += horas
        if condicion.requiere_mantencion:
            activo.cambiar_estado(
                EstadoActivo.MANTENCION, usuario,
                f"Devuelto de {prestamo.folio} en condición '{condicion}'", bodega=bodega_recepcion,
            )
            crear_correctiva(activo, f"Devuelto en condición '{condicion}' desde préstamo {prestamo.folio}.", usuario)
        else:
            activo.cambiar_estado(
                EstadoActivo.DISPONIBLE, usuario,
                f"Devuelto de {prestamo.folio} ({horas} h de uso)", bodega=bodega_recepcion,
            )

    prestamo.fecha_devolucion = timezone.now()
    prestamo.estado = EstadoPrestamo.por_codigo(EstadoPrestamo.DEVUELTO)
    prestamo.bodega_recepcion = bodega_recepcion
    prestamo.firma_devolucion = firma
    prestamo.devuelto_por = devuelto_por
    prestamo.observaciones_devolucion = observaciones
    prestamo.usuario_recepcion = usuario
    prestamo.save()

    resolver_alertas(usuario, prestamo=prestamo, tipo__codigo__in=[TipoAlerta.MOROSIDAD, TipoAlerta.POR_VENCER])
    reevaluar_bloqueo(prestamo.contratista)
    revisar_mantenciones()  # las nuevas horas pueden haber vencido algún plan
    return prestamo
