# =============================================================================
# Vistas de "core":
#   - Las vistas genéricas de los mantenedores (listar, ver, crear, editar,
#     eliminar) que sirven para CUALQUIER tabla registrada en core/crud.py.
#   - El dashboard (pantalla principal).
# =============================================================================
import datetime
from datetime import timedelta
from decimal import Decimal

from django.contrib import messages                      # mensajes de éxito / error en pantalla
from django.contrib.auth.mixins import PermissionRequiredMixin  # exige un permiso para entrar
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator              # separa los resultados en páginas
from django.db import models
from django.db.models import Count, ProtectedError, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.formats import date_format
from django.views import View

from .crud import REGISTRO


# ==========================================================================
# Utilidades para mostrar valores en las tablas genéricas
# ==========================================================================
# Prepara el valor de una celda para mostrarlo: Sí/No, etiqueta de color, fecha, $...
def celda(obj, nombre, mantenedor):
    """Devuelve un dict {tipo, valor, color} para el template."""
    valor = obj
    # Permite columnas como "ciudad__region" (recorre la relación)
    for parte in nombre.split("__"):
        valor = getattr(valor, parte, None) if valor is not None else None
    if callable(valor):
        valor = valor()
    campo = mantenedor._campo(nombre)
    if campo is not None and getattr(campo, "choices", None):
        valor = getattr(obj, f"get_{nombre}_display")()
    if isinstance(valor, bool):
        return {"tipo": "bool", "valor": valor}            # se muestra como ✔ / ✖
    if valor is None or valor == "":
        return {"tipo": "texto", "valor": "—"}             # vacío -> guion
    if hasattr(valor, "color") and isinstance(getattr(valor, "color"), str):
        return {"tipo": "badge", "valor": str(valor), "color": valor.color}  # estados con color
    if isinstance(valor, datetime.datetime):
        return {"tipo": "texto", "valor": date_format(timezone.localtime(valor), "d-m-Y H:i")}
    if hasattr(valor, "isoformat"):
        return {"tipo": "texto", "valor": date_format(valor, "d-m-Y")}
    if isinstance(valor, Decimal) and campo is not None and "$" in str(campo.verbose_name):
        return {"tipo": "texto", "valor": f"$ {valor:,.0f}".replace(",", ".")}  # formato pesos
    return {"tipo": "texto", "valor": str(valor)}


# Busca la configuración de la tabla según el slug de la URL; si no existe -> 404
def obtener_mantenedor(slug):
    try:
        return REGISTRO[slug]
    except KeyError:
        raise Http404("Mantenedor inexistente")


# URL para ver el detalle de un registro (algunas tablas tienen su propia pantalla)
def url_detalle(m, obj):
    if m.url_detalle:
        return reverse(m.url_detalle, args=[obj.pk])
    return reverse("crud_detalle", args=[m.slug, obj.pk])


# Mixin = pieza que se agrega a una vista. Este revisa el permiso del rol
# antes de entrar (por defecto el permiso "view" de la tabla).
class MantenedorMixin(PermissionRequiredMixin):
    accion = "view"

    def dispatch(self, request, *args, **kwargs):
        self.m = obtener_mantenedor(kwargs["slug"])
        return super().dispatch(request, *args, **kwargs)

    # Permiso necesario, ej: "inventario.view_activo"
    def get_permission_required(self):
        return [self.m.perm(self.accion)]

    # Datos comunes para los templates: qué botones puede ver el usuario
    def contexto(self, **extra):
        u = self.request.user
        ctx = {
            "m": self.m,
            "puede_crear": self.m.permite_crear and u.has_perm(self.m.perm("add")),
            "puede_editar": self.m.permite_editar and u.has_perm(self.m.perm("change")),
            "puede_eliminar": self.m.permite_eliminar and u.has_perm(self.m.perm("delete")),
            "url_crear": reverse(self.m.url_crear) if self.m.url_crear else reverse("crud_crear", args=[self.m.slug]),
        }
        ctx.update(extra)
        return ctx


# ==========================================================================
# CRUD genérico
# ==========================================================================
# LISTAR: muestra la tabla con buscador, filtros, orden y paginación
class CrudListView(MantenedorMixin, View):
    def get(self, request, slug):
        m = self.m
        qs = m.get_queryset(request)
        # Buscador: busca el texto en los campos configurados (icontains = "contiene")
        q = request.GET.get("q", "").strip()
        if q and m.busqueda:
            filtro = Q()
            for campo in m.busqueda:
                filtro |= Q(**{f"{campo}__icontains": q})   # | = "o" (cualquiera de los campos)
            qs = qs.filter(filtro)

        # Filtros (listas desplegables): Sí/No, relaciones (FK) u opciones fijas
        filtros_ui = []
        for nombre in m.filtros:
            campo = m._campo(nombre)
            valor = request.GET.get(nombre, "")
            if isinstance(campo, models.BooleanField):
                opciones = [("1", "Sí"), ("0", "No")]
                if valor in ("1", "0"):
                    qs = qs.filter(**{nombre: valor == "1"})
            elif isinstance(campo, models.ForeignKey):
                opciones = [(str(o.pk), str(o)) for o in campo.related_model._default_manager.all()]
                if valor:
                    qs = qs.filter(**{f"{nombre}_id": valor})
            elif campo is not None and campo.choices:
                opciones = [(str(k), v) for k, v in campo.choices]
                if valor:
                    qs = qs.filter(**{nombre: valor})
            else:
                continue
            filtros_ui.append({"nombre": nombre, "etiqueta": m.etiqueta(nombre), "opciones": opciones, "valor": valor})

        # Orden al hacer clic en el encabezado de una columna (?o=campo o ?o=-campo)
        orden = request.GET.get("o", "")
        if orden.lstrip("-") in [c for c in m.columnas if m._campo(c) is not None]:
            qs = qs.order_by(orden)

        # Paginación: 15 registros por página
        pagina = Paginator(qs, 15).get_page(request.GET.get("page"))
        # Arma las filas con las celdas ya preparadas y los botones extra
        filas = [
            {"obj": o, "celdas": [celda(o, c, m) for c in m.columnas], "url_detalle": url_detalle(m, o),
             "acciones": m.acciones(o, request.user) if m.acciones else []}
            for o in pagina
        ]
        columnas = [
            {"nombre": c, "etiqueta": m.etiqueta(c), "ordenable": m._campo(c) is not None}
            for c in m.columnas
        ]
        params = request.GET.copy()
        params.pop("page", None)
        return render(request, "core/crud_list.html", self.contexto(
            pagina=pagina, filas=filas, columnas=columnas, q=q, filtros=filtros_ui,
            orden=orden, querystring=params.urlencode(), total=pagina.paginator.count,
        ))


# VER: muestra todos los campos de un registro
class CrudDetailView(MantenedorMixin, View):
    def get(self, request, slug, pk):
        obj = get_object_or_404(self.m.get_queryset(request), pk=pk)  # si no existe -> 404
        campos = []
        for f in obj._meta.fields:
            if f.name == "id":
                continue
            campos.append({"etiqueta": str(f.verbose_name).capitalize(), **celda(obj, f.name, self.m)})
        return render(request, "core/crud_detail.html", self.contexto(obj=obj, campos=campos))


# CREAR y EDITAR: la misma vista sirve para los dos (si viene pk, es editar)
class CrudFormView(MantenedorMixin, View):
    accion = "add"  # crear exige el permiso "add"

    def dispatch(self, request, *args, **kwargs):
        m = obtener_mantenedor(kwargs["slug"])
        self.obj = None
        if "pk" in kwargs:
            self.accion = "change"  # editar exige el permiso "change"
            if not m.permite_editar:
                raise PermissionDenied
            self.obj = get_object_or_404(m.get_queryset(request), pk=kwargs["pk"])
        elif not m.permite_crear:
            raise PermissionDenied
        elif m.url_crear:
            # Algunas tablas se crean con un flujo propio (ej: préstamo con firma)
            return redirect(m.url_crear)
        return super().dispatch(request, *args, **kwargs)

    def render_form(self, form):
        return render(self.request, "core/crud_form.html", self.contexto(form=form, obj=self.obj))

    # GET: muestra el formulario (vacío para crear, con datos para editar)
    def get(self, request, slug, pk=None):
        form = self.m.get_form_class()(instance=self.obj, initial=request.GET.dict() if not self.obj else None)
        return self.render_form(form)

    # POST: recibe el formulario enviado, lo valida y guarda
    def post(self, request, slug, pk=None):
        form = self.m.get_form_class()(request.POST, request.FILES, instance=self.obj)
        if not form.is_valid():
            # Si hay errores, vuelve a mostrar el formulario con los errores marcados
            messages.error(request, "Revise los errores del formulario.")
            return self.render_form(form)
        obj = form.save(commit=False)  # arma el objeto sin guardarlo todavía
        creando = obj.pk is None
        # Datos para la trazabilidad (quién hizo el cambio y por qué)
        obj._usuario = request.user
        obj._motivo = "Creación desde mantenedor" if creando else "Edición desde mantenedor"
        if self.m.antes_de_guardar:
            self.m.antes_de_guardar(obj, request, creando)  # ajustes propios de la tabla
        obj.save()  # guarda en la base de datos
        form.save_m2m()
        messages.success(request, f"{self.m.titulo_singular} «{obj}» {'creado' if creando else 'actualizado'} correctamente.")
        if "_otro" in request.POST:
            return redirect("crud_crear", self.m.slug)  # botón "Guardar y crear otro"
        return redirect(url_detalle(self.m, obj))


# ELIMINAR: pide confirmación y borra (si no se está usando)
class CrudDeleteView(MantenedorMixin, View):
    accion = "delete"  # eliminar exige el permiso "delete"

    def dispatch(self, request, *args, **kwargs):
        if not obtener_mantenedor(kwargs["slug"]).permite_eliminar:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)

    def get_obj(self, pk):
        return get_object_or_404(self.m.get_queryset(self.request), pk=pk)

    # GET: pantalla de "¿Seguro que quiere eliminar?"
    def get(self, request, slug, pk):
        return render(request, "core/crud_confirm_delete.html", self.contexto(obj=self.get_obj(pk)))

    # POST: elimina de verdad
    def post(self, request, slug, pk):
        obj = self.get_obj(pk)
        # Los registros de sistema (ej: estado DISPONIBLE) no se pueden borrar
        if getattr(obj, "es_sistema", False):
            messages.error(request, f"«{obj}» es un registro de sistema y no se puede eliminar.")
            return redirect(url_detalle(self.m, obj))
        try:
            obj.delete()
        except ProtectedError as e:
            # PROTECT: si otro registro lo usa (ej: una región con comunas), no se borra
            usados = sorted({str(o._meta.verbose_name_plural) for o in e.protected_objects})
            messages.error(
                request,
                f"No se puede eliminar «{obj}» porque está siendo usado en: {', '.join(usados)}. "
                "Puede marcarlo como no vigente.",
            )
            return redirect(url_detalle(self.m, obj))
        messages.success(request, f"{self.m.titulo_singular} «{obj}» eliminado.")
        return redirect("crud_lista", self.m.slug)


# ==========================================================================
# Dashboard
# ==========================================================================
# Pantalla principal: resumen de préstamos, morosos, bloqueados, mantenciones y alertas
def dashboard(request):
    from alertas.models import Alerta
    from alertas.services import ejecutar_revisiones
    from contratistas.models import Contratista
    from inventario.models import Activo
    from mantenimiento.models import Mantenimiento, PlanMantenimiento
    from parametros.models import EstadoActivo
    from prestamos.models import Prestamo

    # Revisa morosidad, bloqueos y mantenciones cada vez que se abre el dashboard
    ejecutar_revisiones()
    hoy = timezone.localdate()
    # Cantidad de activos por estado (Disponible, En Uso, Mantenimiento, Dado de Baja)
    estados = EstadoActivo.objects.annotate(total=Count("activos")).order_by("orden")
    total_activos = sum(e.total for e in estados) or 1
    # Préstamos que todavía no se devuelven
    abiertos = Prestamo.objects.filter(fecha_devolucion__isnull=True).select_related("contratista", "obra", "estado")
    # Planes de mantención vencidos o por vencer
    planes = [p for p in PlanMantenimiento.objects.filter(vigente=True).select_related("activo") if p.esta_vencido or p.por_vencer]
    ctx = {
        "estados": [{"e": e, "pct": round(e.total * 100 / total_activos)} for e in estados],
        "total_activos": sum(e.total for e in estados),
        "prestamos_abiertos": abiertos.count(),
        "prestamos_atrasados": [p for p in abiertos if p.vencido],
        "por_vencer": abiertos.filter(fecha_compromiso__gte=hoy, fecha_compromiso__lte=hoy + timedelta(days=3)),
        "bloqueados": Contratista.objects.filter(bloqueado=True),
        "ots_abiertas": Mantenimiento.objects.filter(estado__codigo__in=["PROGRAMADA", "EN_PROCESO"]).count(),
        "planes": sorted(planes, key=lambda p: -p.porcentaje_uso)[:8],
        "alertas": Alerta.objects.filter(resuelta=False).select_related("tipo")[:8],
        "alertas_total": Alerta.objects.filter(resuelta=False).count(),
        "valor_inventario": Activo.objects.exclude(estado__codigo="BAJA").aggregate(v=models.Sum("valor_compra"))["v"] or 0,
    }
    return render(request, "core/dashboard.html", ctx)


# Página "Parametrización": muestra todas las tablas configurables
def parametrizacion(request):
    """Índice de todos los mantenedores agrupados."""
    return render(request, "core/mantenedores.html")
