# =============================================================================
# Modelos del inventario (REQUERIMIENTO 1: catálogo de activos con trazabilidad)
#   Obra             -> una construcción de la empresa (edificio, puente...)
#   Bodega           -> donde se guardan las herramientas (central o de una obra)
#   Activo           -> cada herramienta o máquina, con su estado y su bodega
#   MovimientoActivo -> la "hoja de vida": cada cambio de estado o de bodega
# =============================================================================
from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

from parametros.models import CategoriaActivo, Comuna, EstadoActivo, Marca


# Tabla de obras (construcciones que tiene la empresa al mismo tiempo)
class Obra(models.Model):
    codigo = models.CharField("código", max_length=20, unique=True)   # ej: OB-001
    nombre = models.CharField(max_length=150)                         # ej: Edificio Alto Temuco
    direccion = models.CharField("dirección", max_length=200)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT)       # relación con la tabla Comuna
    jefe_obra = models.CharField("jefe de obra", max_length=120, blank=True)
    fecha_inicio = models.DateField("fecha de inicio")
    fecha_termino = models.DateField("fecha de término", null=True, blank=True)  # null=True: puede quedar vacía
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "obra"
        verbose_name_plural = "obras"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"


# Tabla de bodegas. Si "obra" está vacía, es la bodega central
class Bodega(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    obra = models.ForeignKey(
        Obra, on_delete=models.PROTECT, null=True, blank=True, related_name="bodegas",
        help_text="Vacío = bodega central.",
    )
    direccion = models.CharField("dirección", max_length=200)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT)
    # Usuario del sistema a cargo de la bodega. SET_NULL: si se borra el usuario, queda vacío
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

    # True si es la bodega central (no pertenece a ninguna obra)
    @property
    def es_central(self):
        return self.obra_id is None


# Tabla de activos: cada herramienta o máquina de la empresa
class Activo(models.Model):
    """Herramienta o maquinaria ligera. Su 'hoja de vida' es el historial de movimientos."""

    codigo = models.CharField("código", max_length=30, unique=True)   # ej: HE-001
    nombre = models.CharField(max_length=150)
    categoria = models.ForeignKey(CategoriaActivo, on_delete=models.PROTECT, verbose_name="categoría")
    marca = models.ForeignKey(Marca, on_delete=models.PROTECT)
    modelo = models.CharField(max_length=100, blank=True)
    numero_serie = models.CharField("n° de serie", max_length=100, blank=True)
    # Estado actual: Disponible, En Uso, Mantenimiento o Dado de Baja (tabla parametrizada)
    estado = models.ForeignKey(EstadoActivo, on_delete=models.PROTECT, related_name="activos")
    # Bodega donde está ahora la herramienta
    bodega = models.ForeignKey(Bodega, on_delete=models.PROTECT, related_name="activos", verbose_name="bodega actual")
    tarifa_diaria = models.DecimalField("tarifa diaria ($)", max_digits=10, decimal_places=0, default=0)  # lo que se cobra por día
    valor_compra = models.DecimalField("valor de compra ($)", max_digits=12, decimal_places=0, default=0)
    fecha_adquisicion = models.DateField("fecha de adquisición", null=True, blank=True)
    # Horómetro: se suman las horas informadas en cada devolución (sirve para la mantención)
    horas_uso = models.DecimalField("horas de uso acumuladas", max_digits=10, decimal_places=1, default=Decimal("0"))
    observaciones = models.TextField(blank=True)
    creado = models.DateTimeField(auto_now_add=True)      # se llena solo al crear
    actualizado = models.DateTimeField(auto_now=True)     # se actualiza solo al guardar

    class Meta:
        verbose_name = "activo"
        verbose_name_plural = "activos"
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} · {self.nombre}"

    # URL de la hoja de vida del activo
    def get_absolute_url(self):
        return reverse("inventario:activo_detalle", args=[self.pk])

    # ------------------------------------------------------------------
    # Trazabilidad: cada cambio de estado o bodega queda registrado.
    # Las vistas asignan obj._usuario y obj._motivo antes de guardar.
    # ------------------------------------------------------------------
    # Se sobrescribe save() (el método que guarda en la base de datos) para que,
    # además de guardar, registre automáticamente el movimiento en el historial.
    def save(self, *args, **kwargs):
        anterior = None
        if self.pk:
            # Si el activo ya existía, lee cómo estaba ANTES del cambio
            anterior = Activo.objects.filter(pk=self.pk).values("estado_id", "bodega_id").first()
        super().save(*args, **kwargs)  # guarda el activo normalmente
        usuario = getattr(self, "_usuario", None)  # quién hizo el cambio
        motivo = getattr(self, "_motivo", "")      # por qué se hizo
        if anterior is None:
            # Activo nuevo: primer registro de su hoja de vida
            MovimientoActivo.objects.create(
                activo=self, estado_nuevo=self.estado, bodega_destino=self.bodega,
                usuario=usuario, descripcion=motivo or "Alta del activo en el inventario",
            )
        elif anterior["estado_id"] != self.estado_id or anterior["bodega_id"] != self.bodega_id:
            # Cambió el estado o la bodega: se registra el movimiento (de dónde a dónde)
            MovimientoActivo.objects.create(
                activo=self,
                estado_anterior_id=anterior["estado_id"], estado_nuevo=self.estado,
                bodega_origen_id=anterior["bodega_id"], bodega_destino=self.bodega,
                usuario=usuario, descripcion=motivo or "Modificación manual",
            )

    # Cambia el estado del activo (y opcionalmente su bodega) dejando el motivo.
    # Lo usan los flujos: préstamo, devolución, mantención y baja.
    def cambiar_estado(self, codigo_estado, usuario=None, motivo="", bodega=None):
        self.estado = EstadoActivo.por_codigo(codigo_estado)
        if bodega is not None:
            self.bodega = bodega
        self._usuario, self._motivo = usuario, motivo
        self.save()

    # True si el estado actual permite prestarlo (solo "Disponible")
    @property
    def disponible(self):
        return self.estado.permite_prestamo

    # True si alguno de sus planes de mantención está vencido (en ese caso no se presta)
    def mantencion_vencida(self):
        return any(p.esta_vencido for p in self.planes_mantenimiento.filter(vigente=True))


# Tabla de movimientos = hoja de vida del activo (se crea sola desde Activo.save)
class MovimientoActivo(models.Model):
    # CASCADE: si se borra el activo, se borran sus movimientos
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, related_name="movimientos")
    fecha = models.DateTimeField(auto_now_add=True)
    estado_anterior = models.ForeignKey(
        EstadoActivo, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    estado_nuevo = models.ForeignKey(EstadoActivo, on_delete=models.PROTECT, related_name="+")
    bodega_origen = models.ForeignKey(Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    bodega_destino = models.ForeignKey(Bodega, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    descripcion = models.CharField("descripción", max_length=255)  # el motivo del movimiento

    class Meta:
        verbose_name = "movimiento de activo"
        verbose_name_plural = "movimientos de activos (trazabilidad)"
        ordering = ["-fecha", "-id"]  # el más reciente primero

    def __str__(self):
        return f"{self.activo.codigo} · {self.fecha:%d-%m-%Y %H:%M} · {self.descripcion}"
