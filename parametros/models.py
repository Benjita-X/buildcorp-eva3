"""
Tablas de PARAMETRIZACIÓN del sistema.

Nada de valores "en duro": regiones, ciudades, comunas, estados, categorías,
marcas, tipos y reglas de negocio viven en tablas propias y se administran
desde su mantenedor (templates) y desde Django Admin.

Los registros con `es_sistema=True` son usados por la lógica de negocio a
través de su `codigo`, por lo que no se pueden eliminar ni cambiar su código.
"""
# Recordatorio: cada clase que hereda de models.Model es una TABLA en PostgreSQL
# y cada atributo (CharField, ForeignKey, ...) es una COLUMNA.
from decimal import Decimal, InvalidOperation

from django.db import models

# Colores disponibles para los estados (se muestran como etiquetas de color)
COLORES = [
    ("primary", "Azul"),
    ("secondary", "Gris"),
    ("success", "Verde"),
    ("danger", "Rojo"),
    ("warning", "Amarillo"),
    ("info", "Celeste"),
    ("dark", "Negro"),
]


# Clase base (abstracta = no crea tabla) que agrega el campo "vigente" a otras tablas.
# Vigente = activo. En vez de borrar un registro que se usa, se marca como no vigente.
class Vigente(models.Model):
    vigente = models.BooleanField("vigente", default=True)

    class Meta:
        abstract = True


# --------------------------------------------------------------------------
# División territorial: Región -> Ciudad -> Comuna
# --------------------------------------------------------------------------
# Tabla de regiones de Chile
class Region(Vigente):
    codigo = models.CharField("código", max_length=5, unique=True, help_text="Ej: IX, RM")  # unique = no se repite
    nombre = models.CharField(max_length=100, unique=True)
    orden = models.PositiveSmallIntegerField(default=0)  # orden de norte a sur

    class Meta:
        verbose_name = "región"           # nombre en singular (para pantallas y admin)
        verbose_name_plural = "regiones"  # nombre en plural
        ordering = ["orden", "nombre"]    # orden por defecto al consultar

    # __str__ = cómo se muestra el registro como texto (en listas, selects, etc.)
    def __str__(self):
        return self.nombre


# Tabla de ciudades. Cada ciudad pertenece a una región (ForeignKey = relación)
class Ciudad(Vigente):
    # on_delete=PROTECT: no se puede borrar una región que tiene ciudades
    region = models.ForeignKey(Region, on_delete=models.PROTECT, related_name="ciudades", verbose_name="región")
    nombre = models.CharField(max_length=100)

    class Meta:
        verbose_name = "ciudad"
        verbose_name_plural = "ciudades"
        ordering = ["region__orden", "nombre"]
        # No se puede repetir el mismo nombre de ciudad dentro de una región
        constraints = [models.UniqueConstraint(fields=["region", "nombre"], name="ciudad_unica_por_region")]

    def __str__(self):
        return self.nombre


# Tabla de comunas. Cada comuna pertenece a una ciudad
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

    # Propiedad: la región de la comuna (a través de su ciudad)
    @property
    def region(self):
        return self.ciudad.region

    @property
    def ubicacion(self):
        return f"{self.nombre}, {self.ciudad.region.nombre}"


# --------------------------------------------------------------------------
# Catálogos simples
# --------------------------------------------------------------------------
# Categorías de herramientas (eléctricas, maquinaria ligera, medición...)
class CategoriaActivo(Vigente):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.TextField("descripción", blank=True)  # blank=True = opcional

    class Meta:
        verbose_name = "categoría de activo"
        verbose_name_plural = "categorías de activo"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# Marcas de herramientas (Bosch, Makita, Honda...)
class Marca(Vigente):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = "marca"
        verbose_name_plural = "marcas"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


# Cargos de los responsables de obra (jefe de obra, capataz, supervisor...)
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
# Clase base para los estados y tipos. Tiene un "codigo" fijo que usa el código
# del sistema (ej: DISPONIBLE) y un "nombre" que se puede cambiar libremente.
class ParametroCodificado(Vigente):
    codigo = models.SlugField(
        "código", max_length=30, unique=True,
        help_text="Identificador interno en MAYÚSCULAS. Los de sistema no se pueden cambiar.",
    )
    nombre = models.CharField(max_length=100)                                   # texto que se muestra
    color = models.CharField(max_length=10, choices=COLORES, default="secondary")  # color de la etiqueta
    orden = models.PositiveSmallIntegerField(default=0)
    # es_sistema=True: lo usan las reglas de negocio, por eso no se puede borrar
    es_sistema = models.BooleanField(
        "de sistema", default=False, editable=False,
        help_text="Usado por las reglas de negocio; no se puede eliminar.",
    )

    class Meta:
        abstract = True
        ordering = ["orden", "nombre"]

    def __str__(self):
        return self.nombre

    # Busca un registro por su código, ej: EstadoActivo.por_codigo("DISPONIBLE")
    @classmethod
    def por_codigo(cls, codigo):
        return cls.objects.get(codigo=codigo)


# Estados de un activo: Disponible, En Uso, Mantenimiento, Dado de Baja (Requerimiento 1)
class EstadoActivo(ParametroCodificado):
    DISPONIBLE, EN_USO, MANTENCION, BAJA = "DISPONIBLE", "EN_USO", "MANTENCION", "BAJA"
    permite_prestamo = models.BooleanField("permite préstamo", default=False)  # solo "Disponible" se puede prestar

    class Meta(ParametroCodificado.Meta):
        verbose_name = "estado de activo"
        verbose_name_plural = "estados de activo"


# Estados de un préstamo: Vigente, Atrasado (moroso), Devuelto
class EstadoPrestamo(ParametroCodificado):
    VIGENTE, ATRASADO, DEVUELTO = "VIGENTE", "ATRASADO", "DEVUELTO"

    class Meta(ParametroCodificado.Meta):
        verbose_name = "estado de préstamo"
        verbose_name_plural = "estados de préstamo"


# Estados de una orden de trabajo: Programada, En proceso, Completada, Cancelada
class EstadoMantenimiento(ParametroCodificado):
    PROGRAMADA, EN_PROCESO, COMPLETADA, CANCELADA = "PROGRAMADA", "EN_PROCESO", "COMPLETADA", "CANCELADA"

    class Meta(ParametroCodificado.Meta):
        verbose_name = "estado de mantenimiento"
        verbose_name_plural = "estados de mantenimiento"


# Tipos de mantenimiento: Preventivo (antes de que falle) o Correctivo (ya falló)
class TipoMantenimiento(ParametroCodificado):
    PREVENTIVO, CORRECTIVO = "PREVENTIVO", "CORRECTIVO"
    descripcion = models.TextField("descripción", blank=True)

    class Meta(ParametroCodificado.Meta):
        verbose_name = "tipo de mantenimiento"
        verbose_name_plural = "tipos de mantenimiento"


# Tipos de alerta: morosidad, bloqueo de contratista, mantención, préstamo por vencer
class TipoAlerta(ParametroCodificado):
    MOROSIDAD, BLOQUEO, MANTENCION, POR_VENCER = "MOROSIDAD", "BLOQUEO", "MANTENCION", "POR_VENCER"

    class Meta(ParametroCodificado.Meta):
        verbose_name = "tipo de alerta"
        verbose_name_plural = "tipos de alerta"


# Condición en que se devuelve una herramienta: Buen estado, Con daños, Con falla
class CondicionActivo(ParametroCodificado):
    """Condición en que se devuelve una herramienta."""
    BUENA, DANADA, FALLA = "BUENA", "DANADA", "FALLA"
    # Si es True, al devolverla en esta condición se crea una orden de trabajo correctiva
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
# Valores que controlan las reglas automáticas. Se cambian en "Reglas de negocio"
# sin tocar el código (por ejemplo, los días de gracia antes de considerar moroso).
class ParametroSistema(models.Model):
    DIAS_GRACIA = "DIAS_GRACIA_DEVOLUCION"     # días extra antes de considerar atrasado
    MAX_MOROSOS = "MAX_PRESTAMOS_MOROSOS"      # cuántos préstamos atrasados provocan el bloqueo
    BLOQUEO_AUTO = "BLOQUEO_AUTOMATICO"        # 1 = bloqueo automático, 0 = solo manual
    DIAS_AVISO_MANT = "DIAS_AVISO_MANTENCION"  # días de anticipación para avisar una mantención
    HORAS_AVISO_MANT = "HORAS_AVISO_MANTENCION"  # horas de anticipación para avisar una mantención
    DIAS_AVISO_VENC = "DIAS_AVISO_VENCIMIENTO"   # días de anticipación para avisar que vence un préstamo

    clave = models.SlugField(max_length=50, unique=True)  # identificador, ej: BLOQUEO_AUTOMATICO
    nombre = models.CharField(max_length=120)             # texto que se muestra
    valor = models.CharField(max_length=100)              # el valor configurado
    descripcion = models.TextField("descripción", blank=True)
    es_sistema = models.BooleanField("de sistema", default=False, editable=False)

    class Meta:
        verbose_name = "parámetro del sistema"
        verbose_name_plural = "parámetros del sistema"
        ordering = ["clave"]

    def __str__(self):
        return f"{self.nombre} = {self.valor}"

    # Lee el valor de un parámetro como número; si no existe, devuelve el valor por defecto
    @classmethod
    def get(cls, clave, defecto=0):
        """Devuelve el valor numérico (Decimal) de un parámetro, o el defecto."""
        try:
            return Decimal(cls.objects.get(clave=clave).valor.replace(",", "."))
        except (cls.DoesNotExist, InvalidOperation):
            return Decimal(defecto)

    # Igual que get(), pero devuelve un número entero
    @classmethod
    def get_int(cls, clave, defecto=0):
        return int(cls.get(clave, defecto))
