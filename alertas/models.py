# =============================================================================
# Modelo de alertas (REQUERIMIENTO 4: alertas por morosidad y bloqueo).
# Cada alerta tiene un tipo y puede apuntar a un contratista, préstamo o activo.
# =============================================================================
from django.conf import settings
from django.db import models
from django.utils import timezone

from contratistas.models import Contratista
from inventario.models import Activo
from parametros.models import TipoAlerta
from prestamos.models import Prestamo


# Tabla de alertas (las crea el sistema automáticamente)
class Alerta(models.Model):
    tipo = models.ForeignKey(TipoAlerta, on_delete=models.PROTECT)
    mensaje = models.CharField(max_length=255)
    fecha = models.DateTimeField(auto_now_add=True)
    contratista = models.ForeignKey(Contratista, on_delete=models.CASCADE, null=True, blank=True, related_name="alertas")
    prestamo = models.ForeignKey(Prestamo, on_delete=models.CASCADE, null=True, blank=True, related_name="alertas")
    activo = models.ForeignKey(Activo, on_delete=models.CASCADE, null=True, blank=True, related_name="alertas")
    resuelta = models.BooleanField(default=False)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)
    resuelta_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "alerta"
        verbose_name_plural = "alertas"
        ordering = ["resuelta", "-fecha"]

    def __str__(self):
        return f"[{self.tipo}] {self.mensaje}"

    # Marca la alerta como resuelta, con la fecha y quién la resolvió
    def resolver(self, usuario=None):
        self.resuelta = True
        self.fecha_resolucion = timezone.now()
        self.resuelta_por = usuario
        self.save(update_fields=["resuelta", "fecha_resolucion", "resuelta_por"])
