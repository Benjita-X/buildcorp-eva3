from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils import timezone

from inventario.models import Activo
from parametros.models import EstadoMantenimiento, ParametroSistema, TipoMantenimiento


class PlanMantenimiento(models.Model):
    """Regla de mantenimiento preventivo: cada N horas de uso y/o cada N días."""

    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="planes_mantenimiento")
    tipo = models.ForeignKey(TipoMantenimiento, on_delete=models.PROTECT)
    descripcion = models.CharField("descripción", max_length=200)
    cada_horas = models.DecimalField("cada (horas de uso)", max_digits=8, decimal_places=1, null=True, blank=True)
    cada_dias = models.PositiveIntegerField("cada (días)", null=True, blank=True)
    ultima_fecha = models.DateField("última mantención (fecha)", default=timezone.localdate)
    ultimas_horas = models.DecimalField("horas en la última mantención", max_digits=10, decimal_places=1, default=0)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "plan de mantenimiento preventivo"
        verbose_name_plural = "planes de mantenimiento preventivo"
        ordering = ["activo__codigo"]

    def __str__(self):
        return f"{self.activo.codigo} · {self.descripcion}"

    def clean(self):
        if not self.cada_horas and not self.cada_dias:
            raise ValidationError("Debe indicar una frecuencia por horas de uso, por días, o ambas.")

    @property
    def proxima_fecha(self):
        return self.ultima_fecha + timedelta(days=self.cada_dias) if self.cada_dias else None

    @property
    def proximas_horas(self):
        return self.ultimas_horas + self.cada_horas if self.cada_horas else None

    @property
    def dias_restantes(self):
        return (self.proxima_fecha - timezone.localdate()).days if self.proxima_fecha else None

    @property
    def horas_restantes(self):
        return self.proximas_horas - self.activo.horas_uso if self.proximas_horas is not None else None

    @property
    def esta_vencido(self):
        return (self.dias_restantes is not None and self.dias_restantes <= 0) or (
            self.horas_restantes is not None and self.horas_restantes <= 0
        )

    @property
    def por_vencer(self):
        dias = ParametroSistema.get_int(ParametroSistema.DIAS_AVISO_MANT, 7)
        horas = ParametroSistema.get(ParametroSistema.HORAS_AVISO_MANT, 10)
        return not self.esta_vencido and (
            (self.dias_restantes is not None and self.dias_restantes <= dias)
            or (self.horas_restantes is not None and self.horas_restantes <= horas)
        )

    @property
    def porcentaje_uso(self):
        """% consumido del intervalo (el mayor entre horas y días) para la barra de progreso."""
        valores = []
        if self.cada_horas:
            valores.append((self.activo.horas_uso - self.ultimas_horas) / self.cada_horas * 100)
        if self.cada_dias:
            valores.append(Decimal((timezone.localdate() - self.ultima_fecha).days) / self.cada_dias * 100)
        return int(min(100, max(valores))) if valores else 0


class Mantenimiento(models.Model):
    """Orden de trabajo (OT) de mantenimiento preventivo o correctivo."""

    activo = models.ForeignKey(Activo, on_delete=models.PROTECT, related_name="mantenimientos")
    plan = models.ForeignKey(
        PlanMantenimiento, on_delete=models.SET_NULL, null=True, blank=True, related_name="ordenes"
    )
    tipo = models.ForeignKey(TipoMantenimiento, on_delete=models.PROTECT)
    estado = models.ForeignKey(EstadoMantenimiento, on_delete=models.PROTECT)
    fecha_programada = models.DateField("fecha programada", default=timezone.localdate)
    fecha_inicio = models.DateTimeField("inicio", null=True, blank=True, editable=False)
    fecha_termino = models.DateTimeField("término", null=True, blank=True, editable=False)
    horas_activo = models.DecimalField(
        "horas del activo al realizar", max_digits=10, decimal_places=1, null=True, blank=True, editable=False
    )
    tecnico = models.CharField("técnico responsable", max_length=120, blank=True)
    descripcion = models.TextField("trabajo a realizar")
    trabajo_realizado = models.TextField("trabajo realizado", blank=True)
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False
    )
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "orden de mantenimiento"
        verbose_name_plural = "órdenes de mantenimiento"
        ordering = ["-fecha_programada", "-id"]

    def __str__(self):
        return f"{self.folio} · {self.activo.codigo} · {self.tipo}"

    def get_absolute_url(self):
        return reverse("mantenimiento:detalle", args=[self.pk])

    @property
    def folio(self):
        return f"OT-{self.pk:05d}" if self.pk else "OT-NUEVA"

    @property
    def abierta(self):
        return self.estado.codigo in (EstadoMantenimiento.PROGRAMADA, EstadoMantenimiento.EN_PROCESO)
