# =============================================================================
# Modelos de préstamos (REQUERIMIENTO 2: entrega y devolución con firma digital)
#   Prestamo        -> la entrega: contratista, responsable, obra, fechas y firmas
#   DetallePrestamo -> cada herramienta incluida en el préstamo
# =============================================================================
import math
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from contratistas.models import Contratista, ResponsableObra
from inventario.models import Activo, Bodega, Obra
from parametros.models import CondicionActivo, EstadoPrestamo


# Tabla de préstamos (cada entrega de herramientas a un contratista)
class Prestamo(models.Model):
    contratista = models.ForeignKey(Contratista, on_delete=models.PROTECT, related_name="prestamos")
    responsable = models.ForeignKey(
        ResponsableObra, on_delete=models.PROTECT, related_name="prestamos", verbose_name="responsable de obra"
    )
    obra = models.ForeignKey(Obra, on_delete=models.PROTECT, related_name="prestamos")
    estado = models.ForeignKey(EstadoPrestamo, on_delete=models.PROTECT, related_name="prestamos")
    fecha_entrega = models.DateTimeField("fecha de entrega", default=timezone.now)
    fecha_compromiso = models.DateField("devolución comprometida")
    fecha_devolucion = models.DateTimeField("fecha de devolución", null=True, blank=True)
    bodega_recepcion = models.ForeignKey(
        Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="+", verbose_name="bodega de recepción"
    )
    # Firmas digitales: se guardan como imagen PNG en texto base64 (viene del <canvas> del navegador)
    firma_entrega = models.TextField("firma de entrega (responsable)")
    firma_devolucion = models.TextField("firma de devolución", blank=True)
    devuelto_por = models.CharField("devuelto por", max_length=150, blank=True)
    observaciones = models.TextField(blank=True)
    observaciones_devolucion = models.TextField("observaciones de devolución", blank=True)
    # Usuarios del sistema que registraron la entrega y la recepción
    usuario_entrega = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="prestamos_entregados"
    )
    usuario_recepcion = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True, related_name="prestamos_recibidos"
    )

    class Meta:
        verbose_name = "préstamo"
        verbose_name_plural = "préstamos"
        ordering = ["-fecha_entrega"]

    def __str__(self):
        return f"{self.folio} · {self.contratista.razon_social}"

    # URL del comprobante del préstamo
    def get_absolute_url(self):
        return reverse("prestamos:detalle", args=[self.pk])

    # Número del préstamo con formato, ej: P-00001
    @property
    def folio(self):
        return f"P-{self.pk:05d}" if self.pk else "P-NUEVO"

    # True si todavía no se devuelve (no tiene fecha de devolución)
    @property
    def abierto(self):
        return self.fecha_devolucion is None

    # ---------------- Cálculo de cobro ----------------
    # Fecha hasta la que se cobra: la devolución, o hoy si todavía no devuelve
    def _fin(self):
        return self.fecha_devolucion or timezone.now()

    # Días que se cobran (redondea hacia arriba; mínimo 1 día). 86400 segundos = 1 día
    @property
    def dias_cobro(self):
        """Días calendario facturables (mínimo 1)."""
        segundos = (self._fin() - self.fecha_entrega).total_seconds()
        return max(1, math.ceil(segundos / 86400))

    # Días de atraso respecto a la fecha comprometida
    @property
    def dias_atraso(self):
        fin = timezone.localdate(self._fin())
        return max(0, (fin - self.fecha_compromiso).days)

    # True si sigue abierto y ya pasó la fecha comprometida (moroso)
    @property
    def vencido(self):
        return self.abierto and timezone.localdate() > self.fecha_compromiso

    # Suma de las tarifas diarias de todas las herramientas del préstamo
    @property
    def tarifa_diaria_total(self):
        return sum((d.tarifa_diaria for d in self.detalles.all()), Decimal("0"))

    # Tarifa diaria total x días
    @property
    def subtotal(self):
        return self.tarifa_diaria_total * self.dias_cobro

    @property
    def total(self):
        """Cobro exacto: tarifa diaria pactada x días facturables (incluye los días de atraso)."""
        return self.subtotal


# Tabla con cada herramienta del préstamo (CASCADE: si se borra el préstamo, se borran sus detalles)
class DetallePrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name="detalles")
    activo = models.ForeignKey(Activo, on_delete=models.PROTECT, related_name="detalles_prestamo")
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="+")
    # Tarifa guardada al momento del préstamo: si después cambia la tarifa, este cobro no cambia
    tarifa_diaria = models.DecimalField("tarifa diaria pactada", max_digits=10, decimal_places=0)
    # Horas de uso y condición se informan al devolver
    horas_uso = models.DecimalField("horas de uso informadas", max_digits=8, decimal_places=1, default=0)
    condicion = models.ForeignKey(
        CondicionActivo, on_delete=models.PROTECT, null=True, blank=True, verbose_name="condición de devolución"
    )
    devuelto = models.BooleanField(default=False)

    class Meta:
        verbose_name = "detalle de préstamo"
        verbose_name_plural = "detalles de préstamo"
        # La misma herramienta no se puede repetir dentro de un préstamo
        constraints = [models.UniqueConstraint(fields=["prestamo", "activo"], name="activo_unico_por_prestamo")]

    def __str__(self):
        return f"{self.prestamo.folio} · {self.activo.codigo}"

    # Lo que se cobra por esta herramienta: tarifa x días
    @property
    def subtotal(self):
        return self.tarifa_diaria * self.prestamo.dias_cobro
