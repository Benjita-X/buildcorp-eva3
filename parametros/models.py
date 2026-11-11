"""
Tablas de PARAMETRIZACIÓN del sistema.

Nada de valores "en duro": regiones, ciudades, comunas, estados, categorías,
marcas, tipos y reglas de negocio viven en tablas propias y se administran
desde su mantenedor (templates) y desde Django Admin.

Los registros con `es_sistema=True` son usados por la lógica de negocio a
través de su `codigo`, por lo que no se pueden eliminar ni cambiar su código.
"""
from decimal import Decimal, InvalidOperation

from django.db import models

COLORES = [
    ("primary", "Azul"),
    ("secondary", "Gris"),
    ("success", "Verde"),
    ("danger", "Rojo"),
    ("warning", "Amarillo"),
    ("info", "Celeste"),
    ("dark", "Negro"),
]


class Vigente(models.Model):
    vigente = models.BooleanField("vigente", default=True)

    class Meta:
        abstract = True


# --------------------------------------------------------------------------
# División territorial: Región -> Ciudad -> Comuna
# --------------------------------------------------------------------------
class Region(Vigente):
    codigo = models.CharField("código", max_length=5, unique=True, help_text="Ej: IX, RM")
    nombre = models.CharField(max_length=100, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "región"
        verbose_name_plural = "regiones"
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre


class Ciudad(Vigente):
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="ciudades", verbose_name="región")
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = "ciudad"
        verbose_name_plural = "ciudades"
        ordering = ["region__orden", "nombre"]
        constraints = [models.UniqueConstraint(fields=["region", "nombre"], name="ciudad_unica_por_region")]

    def __str__(self):
        return self.nombre


class Comuna(Vigente):
    ciudad = models.ForeignKey(Ciudad, on_delete=models.PROTECT, related_name="comunas")
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = "comuna"
        verbose_name_plural = "comunas"
        ordering = ["nombre"]
        constraints = [models.UniqueConstraint(fields=["ciudad", "nombre"], name="comuna_unica_por_ciudad")]

    def __str__(self):
        return self.nombre

    @property
    def region(self):
        return self.ciudad.region

    @property
    def ubicacion(self):
        return f"{self.nombre}, {self.ciudad.region.nombre}"


# --------------------------------------------------------------------------
# Catálogos simples
# --------------------------------------------------------------------------
class CategoriaActivo(Vigente):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)

    class Meta:
        verbose_name = "categoría de activo"
        verbose_name_plural = "categorías de activo"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Marca(Vigente):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "marca"
        verbose_name_plural = "marcas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cargo(Vigente):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "cargo"
        verbose_name_plural = "cargos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# --------------------------------------------------------------------------
# Estados / tipos con código de sistema
# --------------------------------------------------------------------------
class ParametroCodificado(Vigente):
    codigo = models.SlugField(
        "código", max_length=30, unique=True,
        help_text="Identificador interno en MAYÚSCULAS. Los de sistema no se pueden cambiar.",
    )
    nombre = models.CharField(max_length=100)
    color = models.CharField(max_length=10, choices=COLORES, default="secondary")
    orden = models.PositiveSmallIntegerField(default=0)
    es_sistema = models.BooleanField(
        "de sistema", default=False, editable=False,
        help_text="Usado por las reglas de negocio; no se puede eliminar.",
    )

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    @classmethod
    def por_codigo(cls, codigo):
        return cls.objects.get(codigo=codigo)


class EstadoActivo(ParametroCodificado):
    DISPONIBLE, EN_USO, MANTENCION, BAJA = "DISPONIBLE", "EN_USO", "MANTENCION", "BAJA"
    permite_prestamo = models.BooleanField("permite préstamo", default=False)

    class Meta(ParametroCodificado.Meta):
        verbose_name = "estado de activo"
        verbose_name_plural = "estados de activo"


class EstadoPrestamo(ParametroCodificado):
    VIGENTE, ATRASADO, DEVUELTO = "VIGENTE", "ATRASADO", "DEVUELTO"

    class Meta(ParametroCodificado.Meta):
        verbose_name = "estado de préstamo"
        verbose_name_plural = "estados de préstamo"


class EstadoMantenimiento(ParametroCodificado):
    PROGRAMADA, EN_PROCESO, COMPLETADA, CANCELADA = "PROGRAMADA", "EN_PROCESO", "COMPLETADA", "CANCELADA"

    class Meta(ParametroCodificado.Meta):
        verbose_name = "estado de mantenimiento"
        verbose_name_plural = "estados de mantenimiento"


class TipoMantenimiento(ParametroCodificado):
    PREVENTIVO, CORRECTIVO = "PREVENTIVO", "CORRECTIVO"
    descripcion = models.TextField("descripción", blank=True)

    class Meta(ParametroCodificado.Meta):
        verbose_name = "tipo de mantenimiento"
        verbose_name_plural = "tipos de mantenimiento"


class TipoAlerta(ParametroCodificado):
    MOROSIDAD, BLOQUEO, MANTENCION, POR_VENCER = "MOROSIDAD", "BLOQUEO", "MANTENCION", "POR_VENCER"

    class Meta(ParametroCodificado.Meta):
        verbose_name = "tipo de alerta"
        verbose_name_plural = "tipos de alerta"


class CondicionActivo(ParametroCodificado):
    """Condición en que se devuelve una herramienta."""
    BUENA, DANADA, FALLA = "BUENA", "DANADA", "FALLA"
    requiere_mantencion = models.BooleanField(
        "requiere mantención", default=False,
        help_text="Si se devuelve en esta condición, el activo pasa a Mantenimiento y se crea una OT correctiva.",
    )

    class Meta(ParametroCodificado.Meta):
        verbose_name = "condición de devolución"
        verbose_name_plural = "condiciones de devolución"


# --------------------------------------------------------------------------
# Parámetros de reglas de negocio (clave / valor)
# --------------------------------------------------------------------------
class ParametroSistema(models.Model):
    DIAS_GRACIA = "DIAS_GRACIA_DEVOLUCION"
    MAX_MOROSOS = "MAX_PRESTAMOS_MOROSOS"
    BLOQUEO_AUTO = "BLOQUEO_AUTOMATICO"
    DIAS_AVISO_MANT = "DIAS_AVISO_MANTENCION"
    HORAS_AVISO_MANT = "HORAS_AVISO_MANTENCION"
    DIAS_AVISO_VENC = "DIAS_AVISO_VENCIMIENTO"

    clave = models.SlugField(max_length=50, unique=True)
    nombre = models.CharField(max_length=120)
    valor = models.CharField(max_length=100)
    descripcion = models.TextField("descripción", blank=True)
    es_sistema = models.BooleanField("de sistema", default=False, editable=False)

    class Meta:
        verbose_name = "parámetro del sistema"
        verbose_name_plural = "parámetros del sistema"
        ordering = ["clave"]

    def __str__(self):
        return f"{self.nombre} = {self.valor}"

    @classmethod
    def get(cls, clave, defecto=0):
        """Devuelve el valor numérico (Decimal) de un parámetro, o el defecto."""
        try:
            return Decimal(cls.objects.get(clave=clave).valor.replace(",", "."))
        except (cls.DoesNotExist, InvalidOperation):
            return Decimal(defecto)

    @classmethod
    def get_int(cls, clave, defecto=0):
        return int(cls.get(clave, defecto))
