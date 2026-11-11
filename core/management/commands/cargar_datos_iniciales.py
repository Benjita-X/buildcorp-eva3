"""
Carga la parametrización base del sistema, crea los roles (grupos) con sus
permisos y, opcionalmente, datos de demostración.

    python manage.py cargar_datos_iniciales           # parámetros + roles
    python manage.py cargar_datos_iniciales --demo    # + usuarios y datos demo

Es idempotente: se puede ejecutar varias veces sin duplicar datos.
"""
import base64
import math
import os
import struct
import zlib
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.validators import digito_verificador
from parametros import models as pm

APPS_DOMINIO = ["parametros", "inventario", "contratistas", "prestamos", "mantenimiento", "alertas"]

TERRITORIO = [
    ("XV", "Arica y Parinacota", {"Arica": ["Arica", "Camarones"]}),
    ("I", "Tarapacá", {"Iquique": ["Iquique", "Alto Hospicio"]}),
    ("II", "Antofagasta", {"Antofagasta": ["Antofagasta", "Mejillones"], "Calama": ["Calama"]}),
    ("III", "Atacama", {"Copiapó": ["Copiapó", "Caldera"]}),
    ("IV", "Coquimbo", {"La Serena": ["La Serena"], "Coquimbo": ["Coquimbo"]}),
    ("V", "Valparaíso", {"Valparaíso": ["Valparaíso"], "Viña del Mar": ["Viña del Mar"], "Quilpué": ["Quilpué"]}),
    ("RM", "Metropolitana de Santiago", {"Santiago": [
        "Santiago", "Providencia", "Las Condes", "Ñuñoa", "Maipú", "Puente Alto", "La Florida"]}),
    ("VI", "Libertador Gral. Bernardo O'Higgins", {"Rancagua": ["Rancagua", "Machalí"]}),
    ("VII", "Maule", {"Talca": ["Talca"], "Curicó": ["Curicó"]}),
    ("XVI", "Ñuble", {"Chillán": ["Chillán", "Chillán Viejo"]}),
    ("VIII", "Biobío", {"Concepción": ["Concepción", "Talcahuano", "San Pedro de la Paz", "Hualpén"],
                        "Los Ángeles": ["Los Ángeles"]}),
    ("IX", "La Araucanía", {"Temuco": ["Temuco", "Padre Las Casas"], "Villarrica": ["Villarrica"],
                            "Pucón": ["Pucón"], "Angol": ["Angol"], "Lautaro": ["Lautaro"],
                            "Nueva Imperial": ["Nueva Imperial"]}),
    ("XIV", "Los Ríos", {"Valdivia": ["Valdivia"]}),
    ("X", "Los Lagos", {"Puerto Montt": ["Puerto Montt"], "Osorno": ["Osorno"]}),
    ("XI", "Aysén del Gral. Carlos Ibáñez del Campo", {"Coyhaique": ["Coyhaique"]}),
    ("XII", "Magallanes y de la Antártica Chilena", {"Punta Arenas": ["Punta Arenas"]}),
]

# (modelo, [(codigo, nombre, color, extras)])
CODIFICADOS = [
    (pm.EstadoActivo, [
        ("DISPONIBLE", "Disponible", "success", {"permite_prestamo": True}),
        ("EN_USO", "En Uso", "primary", {}),
        ("MANTENCION", "Mantenimiento", "warning", {}),
        ("BAJA", "Dado de Baja", "dark", {}),
    ]),
    (pm.EstadoPrestamo, [
        ("VIGENTE", "Vigente", "primary", {}),
        ("ATRASADO", "Atrasado (moroso)", "danger", {}),
        ("DEVUELTO", "Devuelto", "success", {}),
    ]),
    (pm.EstadoMantenimiento, [
        ("PROGRAMADA", "Programada", "info", {}),
        ("EN_PROCESO", "En proceso", "warning", {}),
        ("COMPLETADA", "Completada", "success", {}),
        ("CANCELADA", "Cancelada", "secondary", {}),
    ]),
    (pm.TipoMantenimiento, [
        ("PREVENTIVO", "Preventivo", "info", {"descripcion": "Programado por horas de uso o fecha límite."}),
        ("CORRECTIVO", "Correctivo", "danger", {"descripcion": "Reparación por falla o daño."}),
    ]),
    (pm.TipoAlerta, [
        ("MOROSIDAD", "Morosidad en devolución", "danger", {}),
        ("BLOQUEO", "Bloqueo de contratista", "dark", {}),
        ("MANTENCION", "Mantención", "warning", {}),
        ("POR_VENCER", "Préstamo por vencer", "info", {}),
    ]),
    (pm.CondicionActivo, [
        ("BUENA", "Buen estado", "success", {"requiere_mantencion": False}),
        ("DANADA", "Con daños", "warning", {"requiere_mantencion": True}),
        ("FALLA", "Con falla / no funciona", "danger", {"requiere_mantencion": True}),
    ]),
]

PARAMETROS = [
    ("DIAS_GRACIA_DEVOLUCION", "Días de gracia para devolver", "0",
     "Días después de la fecha comprometida antes de considerar moroso un préstamo."),
    ("MAX_PRESTAMOS_MOROSOS", "Préstamos morosos para bloqueo", "1",
     "Cantidad de préstamos morosos que provoca el bloqueo automático del contratista."),
    ("RECARGO_ATRASO_PCT", "Recargo por atraso (%)", "50",
     "Porcentaje adicional sobre la tarifa diaria por cada día de atraso."),
    ("DIAS_AVISO_MANTENCION", "Aviso de mantención (días)", "7",
     "Días de anticipación para alertar una mantención preventiva por fecha."),
    ("HORAS_AVISO_MANTENCION", "Aviso de mantención (horas)", "10",
     "Horas de uso restantes para alertar una mantención preventiva por uso."),
    ("DIAS_AVISO_VENCIMIENTO", "Aviso de vencimiento de préstamo (días)", "2",
     "Días de anticipación para alertar que un préstamo está por vencer."),
]

ROLES = {
    "Administrador": "__all__",
    "Bodeguero": {
        "add": ["activo", "prestamo", "detalleprestamo", "contratista", "responsableobra", "bodega"],
        "change": ["activo", "prestamo", "detalleprestamo", "contratista", "responsableobra", "bodega", "alerta"],
    },
    "Encargado de Mantención": {
        "add": ["planmantenimiento", "mantenimiento"],
        "change": ["planmantenimiento", "mantenimiento", "activo", "alerta"],
    },
    "Consulta": {},
}


def rut(cuerpo):
    return f"{cuerpo}-{digito_verificador(str(cuerpo))}"


def firma_demo():
    """Genera un PNG con un trazo, para simular firmas en los datos demo."""
    ancho, alto = 160, 50
    filas = []
    for y in range(alto):
        fila = bytearray([0])
        for x in range(ancho):
            en_trazo = abs(y - (25 + int(12 * math.sin(x / 12)))) < 2 and 15 < x < 145
            fila += bytes([0, 0, 0, 255]) if en_trazo else bytes([255, 255, 255, 0])
        filas.append(bytes(fila))
    crudo = zlib.compress(b"".join(filas))

    def chunk(t, d):
        return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", ancho, alto, 8, 6, 0, 0, 0))
    png += chunk(b"IDAT", crudo) + chunk(b"IEND", b"")
    return "data:image/png;base64," + base64.b64encode(png).decode()


class Command(BaseCommand):
    help = "Carga parametrización base, roles y (con --demo) usuarios y datos de demostración."

    def add_arguments(self, parser):
        parser.add_argument("--demo", action="store_true", help="Crea usuarios y datos de demostración")

    @transaction.atomic
    def handle(self, *args, demo=False, **opts):
        self.parametrizacion()
        self.roles()
        if demo:
            self.usuarios()
            self.datos_demo()
        from alertas.services import ejecutar_revisiones

        self.stdout.write(f"Revisión de alertas: {ejecutar_revisiones()}")
        self.stdout.write(self.style.SUCCESS("Datos iniciales cargados."))

    # ------------------------------------------------------------------
    def parametrizacion(self):
        for orden, (codigo, nombre, ciudades) in enumerate(TERRITORIO, start=1):
            region, _ = pm.Region.objects.update_or_create(codigo=codigo, defaults={"nombre": nombre, "orden": orden})
            for ciudad_nombre, comunas in ciudades.items():
                ciudad, _ = pm.Ciudad.objects.get_or_create(region=region, nombre=ciudad_nombre)
                for comuna in comunas:
                    pm.Comuna.objects.get_or_create(ciudad=ciudad, nombre=comuna)

        for modelo, filas in CODIFICADOS:
            for orden, (codigo, nombre, color, extras) in enumerate(filas, start=1):
                obj, creado = modelo.objects.get_or_create(
                    codigo=codigo, defaults={"nombre": nombre, "color": color, "orden": orden, **extras}
                )
                if not obj.es_sistema:
                    obj.es_sistema = True
                    obj.save(update_fields=["es_sistema"])

        for clave, nombre, valor, desc in PARAMETROS:
            obj, _ = pm.ParametroSistema.objects.get_or_create(
                clave=clave, defaults={"nombre": nombre, "valor": valor, "descripcion": desc}
            )
            pm.ParametroSistema.objects.filter(pk=obj.pk).update(es_sistema=True)

        for nombre in ["Herramientas eléctricas", "Maquinaria ligera", "Equipos de medición", "Andamiaje", "Herramientas manuales"]:
            pm.CategoriaActivo.objects.get_or_create(nombre=nombre)
        for nombre in ["Bosch", "Makita", "DeWalt", "Hilti", "Honda", "Stihl", "Husqvarna", "Truper"]:
            pm.Marca.objects.get_or_create(nombre=nombre)
        for nombre in ["Jefe de obra", "Capataz", "Supervisor", "Prevencionista de riesgos", "Maestro mayor"]:
            pm.Cargo.objects.get_or_create(nombre=nombre)
        self.stdout.write("  [OK] Parametrización (territorio, estados, tipos, reglas)")

    def roles(self):
        perms = Permission.objects.filter(content_type__app_label__in=APPS_DOMINIO)
        ver = perms.filter(codename__startswith="view_")
        for nombre, spec in ROLES.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            if spec == "__all__":
                grupo.permissions.set(list(perms) + list(Permission.objects.filter(codename__in=["view_user", "add_user", "change_user", "view_group"])))
                continue
            codenames = [f"{accion}_{modelo}" for accion, modelos in spec.items() for modelo in modelos]
            grupo.permissions.set(list(ver) + list(perms.filter(codename__in=codenames)))
        self.stdout.write("  [OK] Roles: " + ", ".join(ROLES))

    def usuarios(self):
        clave = os.environ.get("DEMO_PASSWORD", "BuildCorp2026")
        datos = [
            ("admin", "Administrador", True, "Ana", "Administradora"),
            ("bodega", "Bodeguero", False, "Bruno", "Bodeguero"),
            ("mantencion", "Encargado de Mantención", False, "Marta", "Mecánica"),
            ("consulta", "Consulta", False, "Carlos", "Consulta"),
        ]
        for username, grupo, es_admin, nombre, apellido in datos:
            u, creado = User.objects.get_or_create(
                username=username, defaults={"first_name": nombre, "last_name": apellido, "email": f"{username}@buildcorp.cl"}
            )
            if creado:
                u.set_password(clave)
            u.is_staff = es_admin
            u.is_superuser = es_admin
            u.save()
            u.groups.set([Group.objects.get(name=grupo)])
        self.stdout.write("  [OK] Usuarios demo: admin, bodega, mantencion, consulta (clave en DEMO_PASSWORD)")

    def datos_demo(self):
        from contratistas.models import Contratista, ResponsableObra
        from inventario.models import Activo, Bodega, Obra
        from mantenimiento.models import PlanMantenimiento
        from prestamos import services
        from prestamos.models import Prestamo

        if Activo.objects.exists():
            self.stdout.write("  · Ya existen activos: se omiten los datos demo.")
            return

        hoy = timezone.localdate()
        admin = User.objects.get(username="admin")
        temuco = pm.Comuna.objects.get(nombre="Temuco")
        plc = pm.Comuna.objects.get(nombre="Padre Las Casas")
        lautaro = pm.Comuna.objects.get(nombre="Lautaro")

        o1 = Obra.objects.create(codigo="OB-001", nombre="Edificio Alto Temuco", direccion="Av. Alemania 0950",
                                 comuna=temuco, jefe_obra="Rodrigo Paillalef", fecha_inicio=hoy - timedelta(days=120))
        o2 = Obra.objects.create(codigo="OB-002", nombre="Condominio Los Robles", direccion="Camino Maquehue 1200",
                                 comuna=plc, jefe_obra="Camila Huenchullán", fecha_inicio=hoy - timedelta(days=60))
        o3 = Obra.objects.create(codigo="OB-003", nombre="Puente Río Cautín", direccion="Ruta 5 Sur km 640",
                                 comuna=lautaro, jefe_obra="Jorge Sandoval", fecha_inicio=hoy - timedelta(days=30))
        central = Bodega.objects.create(nombre="Bodega Central Temuco", direccion="Calle Industrial 455", comuna=temuco)
        Bodega.objects.create(nombre="Bodega Obra Alto Temuco", obra=o1, direccion=o1.direccion, comuna=temuco)
        Bodega.objects.create(nombre="Bodega Obra Los Robles", obra=o2, direccion=o2.direccion, comuna=plc)

        cat = {c.nombre: c for c in pm.CategoriaActivo.objects.all()}
        marca = {m.nombre: m for m in pm.Marca.objects.all()}
        disp = pm.EstadoActivo.por_codigo("DISPONIBLE")
        activos = [
            ("HE-001", "Taladro percutor SDS Plus", "Herramientas eléctricas", "Bosch", "GBH 2-26", 8000, 180000, 120),
            ("HE-002", "Esmeril angular 9\"", "Herramientas eléctricas", "Makita", "GA9020", 6000, 95000, 40),
            ("HE-003", "Sierra circular 7 1/4\"", "Herramientas eléctricas", "DeWalt", "DWE575", 7000, 150000, 65),
            ("HE-004", "Rotomartillo SDS Max", "Herramientas eléctricas", "Hilti", "TE 70-ATC", 15000, 1200000, 210),
            ("HE-005", "Atornillador inalámbrico 18V", "Herramientas eléctricas", "Makita", "DDF482", 5000, 120000, 15),
            ("ML-001", "Generador 5.5 kVA", "Maquinaria ligera", "Honda", "EG5500", 25000, 1500000, 95),
            ("ML-002", "Placa compactadora", "Maquinaria ligera", "Honda", "GX160", 20000, 900000, 30),
            ("ML-003", "Betonera 150 L", "Maquinaria ligera", "Truper", "MEZ-150", 18000, 450000, 12),
            ("ML-004", "Cortadora de pavimento", "Maquinaria ligera", "Husqvarna", "FS 400 LV", 30000, 2500000, 48),
            ("ML-005", "Motosierra", "Maquinaria ligera", "Stihl", "MS 250", 12000, 350000, 22),
            ("ME-001", "Nivel láser rotativo", "Equipos de medición", "Bosch", "GRL 400 H", 10000, 800000, 0),
            ("ME-002", "Medidor láser de distancia", "Equipos de medición", "Bosch", "GLM 50", 3000, 90000, 0),
            ("AN-001", "Andamio modular 1,5 m (cuerpo)", "Andamiaje", "Truper", "AND-150", 3000, 120000, 0),
            ("AN-002", "Andamio modular 1,5 m (cuerpo)", "Andamiaje", "Truper", "AND-150", 3000, 120000, 0),
        ]
        a = {}
        for codigo, nombre, c, mca, modelo, tarifa, valor, horas in activos:
            obj = Activo(codigo=codigo, nombre=nombre, categoria=cat[c], marca=marca[mca], modelo=modelo,
                         numero_serie=f"SN-{codigo}-2025", estado=disp, bodega=central, tarifa_diaria=tarifa,
                         valor_compra=valor, fecha_adquisicion=hoy - timedelta(days=365), horas_uso=Decimal(horas))
            obj._usuario = admin
            obj.save()
            a[codigo] = obj

        preventivo = pm.TipoMantenimiento.por_codigo("PREVENTIVO")
        PlanMantenimiento.objects.create(activo=a["ML-001"], tipo=preventivo, descripcion="Cambio de aceite y filtro",
                                         cada_horas=100, ultimas_horas=0, ultima_fecha=hoy - timedelta(days=40))
        PlanMantenimiento.objects.create(activo=a["HE-004"], tipo=preventivo, descripcion="Revisión de carbones y engrase",
                                         cada_dias=90, ultima_fecha=hoy - timedelta(days=100), ultimas_horas=150)
        PlanMantenimiento.objects.create(activo=a["ML-002"], tipo=preventivo, descripcion="Cambio de aceite del motor",
                                         cada_horas=50, cada_dias=180, ultimas_horas=0, ultima_fecha=hoy - timedelta(days=20))
        PlanMantenimiento.objects.create(activo=a["ML-004"], tipo=preventivo, descripcion="Cambio de disco y correa",
                                         cada_horas=100, ultimas_horas=0, ultima_fecha=hoy - timedelta(days=60))

        cargo = {c.nombre: c for c in pm.Cargo.objects.all()}
        c1 = Contratista.objects.create(rut=rut(76123456), razon_social="Constructora Araucanía SpA", giro="Construcción",
                                        direccion="Av. Caupolicán 1020", comuna=temuco, telefono="+56 45 2123456",
                                        email="contacto@araucania.cl")
        c2 = Contratista.objects.create(rut=rut(77234567), razon_social="Eléctrica Sur Ltda.", giro="Instalaciones eléctricas",
                                        direccion="Pedro de Valdivia 333", comuna=plc, telefono="+56 45 2987654",
                                        email="obras@electricasur.cl")
        c3 = Contratista.objects.create(rut=rut(78345678), razon_social="Hormigones del Cautín S.A.", giro="Obras civiles",
                                        direccion="Ruta S-30 km 3", comuna=lautaro, telefono="+56 45 2555111")
        r1 = ResponsableObra.objects.create(contratista=c1, rut=rut(12345678), nombre="Pedro Millán Rojas", cargo=cargo["Jefe de obra"])
        ResponsableObra.objects.create(contratista=c1, rut=rut(13456789), nombre="Daniela Quilaqueo Soto", cargo=cargo["Capataz"])
        r2 = ResponsableObra.objects.create(contratista=c2, rut=rut(15678901), nombre="Luis Catrileo Vera", cargo=cargo["Supervisor"])
        r3 = ResponsableObra.objects.create(contratista=c3, rut=rut(16789012), nombre="Francisca Neira Lagos", cargo=cargo["Jefe de obra"])

        firma = firma_demo()
        # 1) Préstamo vigente (al día)
        p1 = services.registrar_prestamo(contratista=c1, responsable=r1, obra=o1, fecha_compromiso=hoy + timedelta(days=4),
                                         activos=[a["HE-001"], a["ML-001"]], firma=firma, usuario=admin)
        Prestamo.objects.filter(pk=p1.pk).update(fecha_entrega=timezone.now() - timedelta(days=3))
        # 2) Préstamo moroso -> al revisar, Eléctrica Sur queda bloqueada automáticamente
        p2 = services.registrar_prestamo(contratista=c2, responsable=r2, obra=o2, fecha_compromiso=hoy,
                                         activos=[a["HE-002"], a["AN-001"]], firma=firma, usuario=admin,
                                         observaciones="Trabajos de canalización")
        Prestamo.objects.filter(pk=p2.pk).update(fecha_entrega=timezone.now() - timedelta(days=12),
                                                 fecha_compromiso=hoy - timedelta(days=5))
        # 3) Préstamo ya devuelto
        p3 = services.registrar_prestamo(contratista=c3, responsable=r3, obra=o3, fecha_compromiso=hoy + timedelta(days=1),
                                         activos=[a["ML-003"], a["HE-003"]], firma=firma, usuario=admin)
        buena = pm.CondicionActivo.por_codigo("BUENA")
        services.registrar_devolucion(
            prestamo=p3, devoluciones={d.pk: (Decimal("16"), buena) for d in p3.detalles.all()},
            bodega_recepcion=central, firma=firma, devuelto_por=r3.nombre, usuario=admin,
        )
        Prestamo.objects.filter(pk=p3.pk).update(fecha_entrega=timezone.now() - timedelta(days=20),
                                                 fecha_compromiso=hoy - timedelta(days=14),
                                                 fecha_devolucion=timezone.now() - timedelta(days=15))
        self.stdout.write("  [OK] Datos demo: 3 obras, 3 bodegas, 14 activos, 3 contratistas, 3 préstamos, 4 planes")
