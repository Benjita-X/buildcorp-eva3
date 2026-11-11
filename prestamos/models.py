import math
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone

from contratistas.models import Contratista, ResponsableObra
from inventario.models import Activo, Bodega, Obra
from parametros.models import CondicionActivo, EstadoPrestamo, ParametroSistema


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
    firma_entrega = models.TextField("firma de entrega (responsable)")
    firma_devolucion = models.TextField("firma de devolución", blank=True)
    devuelto_por = models.CharField("devuelto por", max_length=150, blank=True)
    observaciones = models.TextField(blank=True)
    observaciones_devolucion = models.TextField("observaciones de devolución", blank=True)
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

    def get_absolute_url(self):
        return reverse("prestamos:detalle", args=[self.pk])

    @property
    def folio(self):
        return f"P-{self.pk:05d}" if self.pk else "P-NUEVO"

    @property
    def abierto(self):
        return self.fecha_devolucion is None

    # ---------------- Cálculo de cobro ----------------
    def _fin(self):
        return self.fecha_devolucion or timezone.now()

    @property
    def dias_cobro(self):
        """Días calendario facturables (mínimo 1)."""
        segundos = (self._fin() - self.fecha_entrega).total_seconds()
        return max(1, math.ceil(segundos / 86400))

    @property
    def dias_atraso(self):
        fin = timezone.localdate(self._fin())
        return max(0, (fin - self.fecha_compromiso).days)

    @property
    def vencido(self):
        return self.abierto and timezone.localdate() > self.fecha_compromiso

    @property
    def tarifa_diaria_total(self):
        return sum((d.tarifa_diaria for d in self.detalles.all()), Decimal("0"))

    @property
    def subtotal(self):
        return self.tarifa_diaria_total * self.dias_cobro

    @property
    def recargo_pct(self):
        return ParametroSistema.get(ParametroSistema.RECARGO_ATRASO, 50)

    @property
    def recargo(self):
        return (self.tarifa_diaria_total * self.dias_atraso * self.recargo_pct / 100).quantize(Decimal("1"))

    @property
    def total(self):
        return self.subtotal + self.recargo


class DetallePrestamo(models.Model):
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, related_name="detalles")
    activo = models.ForeignKey(Activo, on_delete=models.PROTECT, related_name="detalles_prestamo")
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="+")
    tarifa_diaria = models.DecimalField("tarifa diaria pactada", max_digits=10, decimal_places=0)
    horas_uso = models.DecimalField("horas de uso informadas", max_digits=8, decimal_places=1, default=0)
    condicion = models.ForeignKey(
        CondicionActivo, on_delete=models.PROTECT, null=True, blank=True, verbose_name="condición de devolución"
    )
    devuelto = models.BooleanField(default=False)

    class Meta:
        verbose_name = "detalle de préstamo"
        verbose_name_plural = "detalles de préstamo"
        constraints = [models.UniqueConstraint(fields=["prestamo", "activo"], name="activo_unico_por_prestamo")]

    def __str__(self):
        return f"{self.prestamo.folio} · {self.activo.codigo}"

    @property
    def subtotal(self):
        return self.tarifa_diaria * self.prestamo.dias_cobro
