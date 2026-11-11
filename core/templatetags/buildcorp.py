# =============================================================================
# Filtros y etiquetas propias para los templates.
# Se usan en el HTML con {% load buildcorp %}, por ejemplo: {{ valor|clp }}
# =============================================================================
from decimal import Decimal

from django import template

register = template.Library()


# Filtro "clp": muestra un número como pesos chilenos
@register.filter
def clp(valor):
    """Formatea un número como pesos chilenos: 1234567 -> $ 1.234.567"""
    try:
        return "$ " + f"{Decimal(valor):,.0f}".replace(",", ".")
    except Exception:
        return valor


# Filtro para leer un valor de un diccionario dentro del template
@register.filter
def get_item(diccionario, clave):
    return diccionario.get(clave)


# Resumen con números (KPIs) que se muestra arriba en la portada del Django Admin
@register.inclusion_tag("admin/_resumen.html")
def admin_resumen():
    from alertas.models import Alerta
    from contratistas.models import Contratista
    from inventario.models import Activo
    from prestamos.models import Prestamo

    abiertos = Prestamo.objects.filter(fecha_devolucion__isnull=True)
    return {
        "kpis": [
            ("Activos", Activo.objects.count(), "#0d6efd"),
            ("Préstamos abiertos", abiertos.count(), "#198754"),
            ("Préstamos morosos", sum(1 for p in abiertos if p.vencido), "#dc3545"),
            ("Contratistas bloqueados", Contratista.objects.filter(bloqueado=True).count(), "#212529"),
            ("Alertas pendientes", Alerta.objects.filter(resuelta=False).count(), "#fd7e14"),
        ]
    }
