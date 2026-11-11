# =============================================================================
# Modelos de contratistas:
#   Contratista     -> la EMPRESA subcontratada (ej: Eléctrica Sur Ltda.)
#   ResponsableObra -> la PERSONA de esa empresa que recibe las herramientas y firma
# =============================================================================
from django.db import models
from django.urls import reverse
from django.utils import timezone

from core.validators import normalizar_rut, validar_rut
from parametros.models import Cargo, Comuna


# Tabla de contratistas (empresas a las que se les prestan herramientas)
class Contratista(models.Model):
    rut = models.CharField("RUT", max_length=12, unique=True, validators=[validar_rut])  # valida el dígito verificador
    razon_social = models.CharField("razón social", max_length=150)
    nombre_fantasia = models.CharField("nombre de fantasía", max_length=150, blank=True)
    giro = models.CharField(max_length=150, blank=True)
    direccion = models.CharField("dirección", max_length=200)
    comuna = models.ForeignKey(Comuna, on_delete=models.PROTECT)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    # Datos del bloqueo por morosidad (editable=False: no se editan en el formulario,
    # los cambia el sistema o los botones Bloquear / Desbloquear)
    bloqueado = models.BooleanField(default=False, editable=False)
    bloqueo_automatico = models.BooleanField("bloqueo automático", default=False, editable=False)
    motivo_bloqueo = models.CharField("motivo de bloqueo", max_length=255, blank=True, editable=False)
    fecha_bloqueo = models.DateTimeField("fecha de bloqueo", null=True, blank=True, editable=False)
    vigente = models.BooleanField(default=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "contratista"
        verbose_name_plural = "contratistas"
        ordering = ["razon_social"]

    def __str__(self):
        return f"{self.razon_social} ({self.rut})"

    # URL de la ficha del contratista
    def get_absolute_url(self):
        return reverse("contratistas:detalle", args=[self.pk])

    # Antes de guardar, deja el RUT en formato estándar (sin puntos, con guion)
    def save(self, *args, **kwargs):
        self.rut = normalizar_rut(self.rut)
        super().save(*args, **kwargs)

    # Bloquea al contratista (automatico=True cuando lo hace el sistema por morosidad)
    def bloquear(self, motivo, automatico=False):
        self.bloqueado = True
        self.bloqueo_automatico = automatico
        self.motivo_bloqueo = motivo[:255]
        self.fecha_bloqueo = timezone.now()
        # update_fields: guarda solo estos campos
        self.save(update_fields=["bloqueado", "bloqueo_automatico", "motivo_bloqueo", "fecha_bloqueo"])

    # Quita el bloqueo y limpia el motivo
    def desbloquear(self):
        self.bloqueado = False
        self.bloqueo_automatico = False
        self.motivo_bloqueo = ""
        self.fecha_bloqueo = None
        self.save(update_fields=["bloqueado", "bloqueo_automatico", "motivo_bloqueo", "fecha_bloqueo"])


# Tabla de responsables de obra (personas de cada contratista que firman)
class ResponsableObra(models.Model):
    # Cada responsable pertenece a un contratista
    contratista = models.ForeignKey(Contratista, on_delete=models.PROTECT, related_name="responsables")
    rut = models.CharField("RUT", max_length=12, validators=[validar_rut])
    nombre = models.CharField("nombre completo", max_length=150)
    cargo = models.ForeignKey(Cargo, on_delete=models.PROTECT)  # jefe de obra, capataz, supervisor...
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email = models.EmailField(blank=True)
    vigente = models.BooleanField(default=True)

    class Meta:
        verbose_name = "responsable de obra"
        verbose_name_plural = "responsables de obra"
        ordering = ["nombre"]
        # La misma persona no se puede repetir dentro del mismo contratista
        constraints = [models.UniqueConstraint(fields=["contratista", "rut"], name="responsable_unico_por_contratista")]

    def __str__(self):
        return f"{self.nombre} ({self.contratista.razon_social})"

    def save(self, *args, **kwargs):
        self.rut = normalizar_rut(self.rut)
        super().save(*args, **kwargs)
