from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from parametros.models import CategoriaActivo, Comuna, EstadoActivo, Marca


class Obra(models.Model):
    codigo = models.CharField("código", max_length=20, unique=True)
    nombre = models.CharField(max_length=150)
    direccion = models.CharField("dirección", max_length=200)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT)
    jefe_obra = models.CharField("jefe de obra", max_length=120, blank=True)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_termino = models.DateField("fecha de término", null=True, blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "obra"
        verbose_name_plural = "obras"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


class Bodega(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    obra = models.ForeignKey(
        Obra, on_delete=models.PROTECT, null=True, blank=True, related_name="bodegas",
        help_text="Vacío = bodega central.",
    )
    direccion = models.CharField("dirección", max_length=200)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT)
    encargado = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="bodegas"
    )
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "bodega"
        verbose_name_plural = "bodegas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def es_central(self):
        return self.obra_id is None


class Activo(models.Model):
    """Herramienta o maquinaria ligera. Su 'hoja de vida' es el historial de movimientos."""

    codigo = models.CharField("código", max_length=30, unique=True)
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(CategoriaActivo, on_delete=models.PROTECT, verbose_name="categoría")
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField("n° de serie", max_length=100, blank=True)
    estado = models.ForeignKey(EstadoActivo, on_delete=models.PROTECT, related_name="activos")
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="activos", verbose_name="bodega actual")
    tarifa_diaria = models.DecimalField("tarifa diaria ($)", max_digits=10, decimal_places=0, default=0)
    valor_compra = models.DecimalField("valor de compra ($)", max_digits=12, decimal_places=0, default=0)
    fecha_adquisicion = models.DateField("fecha de adquisición", null=True, blank=True)
    horas_uso = models.DecimalField("horas de uso acumuladas", max_digits=10, decimal_places=1, default=Decimal("0"))
    observaciones = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "activo"
        verbose_name_plural = "activos"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    def get_absolute_url(self):
        return reverse("inventario:activo_detalle", args=[self.pk])

    # ------------------------------------------------------------------
    # Trazabilidad: cada cambio de estado o bodega queda registrado.
    # Las vistas asignan obj._usuario y obj._motivo antes de guardar.
    # ------------------------------------------------------------------
    def save(self, *args, **kwargs):
        anterior = None
        if self.pk:
            anterior = Activo.objects.filter(pk=self.pk).values("estado_id", "bodega_id").first()
        super().save(*args, **kwargs)
        usuario = getattr(self, "_usuario", None)
        motivo = getattr(self, "_motivo", "")
        if anterior is None:
            MovimientoActivo.objects.create(
                activo=self, estado_nuevo=self.estado, bodega_destino=self.bodega,
                usuario=usuario, descripcion=motivo or "Alta del activo en el inventario",
            )
        elif anterior["estado_id"] != self.estado_id or anterior["bodega_id"] != self.bodega_id:
            MovimientoActivo.objects.create(
                activo=self,
                estado_anterior_id=anterior["estado_id"], estado_nuevo=self.estado,
                bodega_origen_id=anterior["bodega_id"], bodega_destino=self.bodega,
                usuario=usuario, descripcion=motivo or "Modificación manual",
            )

    def cambiar_estado(self, codigo_estado, usuario=None, motivo="", bodega=None):
        self.estado = EstadoActivo.por_codigo(codigo_estado)
        if bodega is not None:
            self.bodega = bodega
        self._usuario, self._motivo = usuario, motivo
        self.save()

    @property
    def disponible(self):
        return self.estado.permite_prestamo

    def mantencion_vencida(self):
        return any(p.esta_vencido for p in self.planes_mantenimiento.filter(vigente=True))


class MovimientoActivo(models.Model):
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="movimientos")
    fecha = models.DateTimeField(auto_now_add=True)
    estado_anterior = models.ForeignKey(
        EstadoActivo, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    estado_nuevo = models.ForeignKey(EstadoActivo, on_delete=models.PROTECT, related_name="+")
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField("descripción", max_length=255)

    class Meta:
        verbose_name = "movimiento de activo"
        verbose_name_plural = "movimientos de activos (trazabilidad)"
        ordering = ["-fecha", "-id"]

    def __str__(self):
        return f"{self.activo.codigo} · {self.fecha:%d-%m-%Y %H:%M} · {self.descripcion}"
