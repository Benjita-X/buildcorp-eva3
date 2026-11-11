"""
Pruebas de las reglas de negocio y de seguridad.
    python manage.py test
"""
import io
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from alertas.models import Alerta
from alertas.services import ejecutar_revisiones
from contratistas.models import Contratista
from core.crud import REGISTRO
from core.validators import validar_rut
from inventario.models import Activo, Bodega
from mantenimiento import services as mant
from mantenimiento.models import Mantenimiento
from parametros.models import CondicionActivo, ParametroSistema, Region
from prestamos import services
from prestamos.models import Prestamo

FIRMA = "data:image/png;base64," + "A" * 400


class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_iniciales", "--demo", stdout=io.StringIO())

    def setUp(self):
        self.admin = User.objects.get(username="admin")
        self.c1 = Contratista.objects.get(razon_social__startswith="Constructora")
        self.c2 = Contratista.objects.get(razon_social__startswith="Eléctrica")
        self.c3 = Contratista.objects.get(razon_social__startswith="Hormigones")
        self.central = Bodega.objects.get(nombre="Bodega Central Temuco")

    def disponibles(self, n=1):
        return [a for a in Activo.objects.filter(estado__codigo="DISPONIBLE") if not a.mantencion_vencida()][:n]

    def prestar(self, contratista, activos, dias=3):
        return services.registrar_prestamo(
            contratista=contratista, responsable=contratista.responsables.first(), obra=Prestamo.objects.first().obra,
            fecha_compromiso=timezone.localdate() + timedelta(days=dias), activos=activos, firma=FIRMA, usuario=self.admin,
        )


class ReglasPrestamoTest(BaseTest):
    def test_demo_bloquea_contratista_moroso(self):
        self.c2.refresh_from_db()
        self.assertTrue(self.c2.bloqueado)
        self.assertTrue(self.c2.bloqueo_automatico)
        self.assertTrue(Alerta.objects.filter(tipo__codigo="MOROSIDAD", contratista=self.c2, resuelta=False).exists())

    def test_contratista_bloqueado_no_puede_retirar(self):
        with self.assertRaises(ValidationError) as ctx:
            self.prestar(self.c2, self.disponibles())
        self.assertIn("BLOQUEADO", " ".join(ctx.exception.messages))

    def test_prestamo_cambia_estado_y_registra_trazabilidad(self):
        activo = self.disponibles()[0]
        movimientos = activo.movimientos.count()
        p = self.prestar(self.c3, [activo])
        activo.refresh_from_db()
        self.assertEqual(activo.estado.codigo, "EN_USO")
        self.assertEqual(activo.movimientos.count(), movimientos + 1)
        self.assertEqual(p.detalles.get().tarifa_diaria, activo.tarifa_diaria)

    def test_no_presta_activo_no_disponible(self):
        en_uso = Activo.objects.filter(estado__codigo="EN_USO").first()
        with self.assertRaises(ValidationError):
            self.prestar(self.c3, [en_uso])

    def test_no_presta_activo_con_mantencion_vencida(self):
        he004 = Activo.objects.get(codigo="HE-004")
        self.assertTrue(he004.mantencion_vencida())
        with self.assertRaises(ValidationError):
            self.prestar(self.c3, [he004])

    def test_firma_obligatoria(self):
        with self.assertRaises(ValidationError):
            services.registrar_prestamo(
                contratista=self.c3, responsable=self.c3.responsables.first(), obra=Prestamo.objects.first().obra,
                fecha_compromiso=timezone.localdate(), activos=self.disponibles(), firma="", usuario=self.admin,
            )

    def test_devolucion_suma_horas_y_desbloquea(self):
        p = Prestamo.objects.get(contratista=self.c2, fecha_devolucion__isnull=True)
        buena = CondicionActivo.por_codigo("BUENA")
        horas_antes = {d.activo_id: d.activo.horas_uso for d in p.detalles.all()}
        services.registrar_devolucion(
            prestamo=p, devoluciones={d.pk: (Decimal("8"), buena) for d in p.detalles.all()},
            bodega_recepcion=self.central, firma=FIRMA, devuelto_por="Test", usuario=self.admin,
        )
        for d in p.detalles.all():
            d.activo.refresh_from_db()
            self.assertEqual(d.activo.horas_uso, horas_antes[d.activo_id] + 8)
            self.assertEqual(d.activo.estado.codigo, "DISPONIBLE")
        self.c2.refresh_from_db()
        self.assertFalse(self.c2.bloqueado, "El bloqueo automático debe levantarse al regularizar")
        p.refresh_from_db()
        self.assertGreater(p.dias_atraso, 0, "La devolución fue con atraso")

    def test_devolucion_danada_genera_ot_correctiva(self):
        activo = self.disponibles()[0]
        p = self.prestar(self.c3, [activo])
        danada = CondicionActivo.por_codigo("DANADA")
        services.registrar_devolucion(
            prestamo=p, devoluciones={d.pk: (Decimal("2"), danada) for d in p.detalles.all()},
            bodega_recepcion=self.central, firma=FIRMA, devuelto_por="Test", usuario=self.admin,
        )
        activo.refresh_from_db()
        self.assertEqual(activo.estado.codigo, "MANTENCION")
        self.assertTrue(Mantenimiento.objects.filter(activo=activo, tipo__codigo="CORRECTIVO").exists())

    def test_cobro_tarifa_por_dias(self):
        p = Prestamo.objects.get(contratista=self.c2, fecha_devolucion__isnull=True)
        self.assertEqual(p.total, p.tarifa_diaria_total * p.dias_cobro)

    def test_bloqueo_automatico_se_puede_desactivar(self):
        from alertas.services import reevaluar_bloqueo
        self.c2.desbloquear()
        ParametroSistema.objects.filter(clave="BLOQUEO_AUTOMATICO").update(valor="0")
        reevaluar_bloqueo(self.c2)
        self.c2.refresh_from_db()
        self.assertFalse(self.c2.bloqueado, "Con el parámetro en 0 el bloqueo es solo manual")
        ParametroSistema.objects.filter(clave="BLOQUEO_AUTOMATICO").update(valor="1")
        reevaluar_bloqueo(self.c2)
        self.c2.refresh_from_db()
        self.assertTrue(self.c2.bloqueado)


class MantenimientoTest(BaseTest):
    def test_plan_vencido_genera_ot_y_ciclo_completo(self):
        he004 = Activo.objects.get(codigo="HE-004")
        ot = Mantenimiento.objects.get(activo=he004, estado__codigo="PROGRAMADA")
        mant.iniciar(ot, self.admin)
        he004.refresh_from_db()
        self.assertEqual(he004.estado.codigo, "MANTENCION")
        mant.completar(ot, "Cambio de carbones", "Técnico", self.admin)
        he004.refresh_from_db()
        self.assertEqual(he004.estado.codigo, "DISPONIBLE")
        self.assertFalse(he004.mantencion_vencida())

    def test_mantencion_por_horas_de_uso(self):
        ml001 = Activo.objects.get(codigo="ML-001")  # plan cada 100 h, está prestado con 95 h
        p = ml001.detalles_prestamo.get(devuelto=False).prestamo
        buena = CondicionActivo.por_codigo("BUENA")
        services.registrar_devolucion(
            prestamo=p, devoluciones={d.pk: (Decimal("10"), buena) for d in p.detalles.all()},
            bodega_recepcion=self.central, firma=FIRMA, devuelto_por="Test", usuario=self.admin,
        )
        self.assertTrue(Mantenimiento.objects.filter(activo=ml001, estado__codigo="PROGRAMADA", plan__isnull=False).exists())

    def test_alerta_resuelta_no_reaparece(self):
        from alertas.models import Alerta
        p = Prestamo.objects.get(contratista=self.c2, fecha_devolucion__isnull=True)
        alerta = Alerta.objects.get(prestamo=p, tipo__codigo="MOROSIDAD", resuelta=False)
        alerta.resolver(self.admin)
        ejecutar_revisiones()
        self.assertFalse(Alerta.objects.filter(prestamo=p, tipo__codigo="MOROSIDAD", resuelta=False).exists())

    def test_revision_idempotente(self):
        antes = Alerta.objects.count()
        ejecutar_revisiones()
        ejecutar_revisiones()
        self.assertEqual(Alerta.objects.count(), antes)


class SeguridadYMantenedoresTest(BaseTest):
    def test_rut(self):
        with self.assertRaises(ValidationError):
            validar_rut("12345678-0")
        validar_rut(self.c1.rut)

    def test_requiere_login(self):
        r = self.client.get(reverse("dashboard"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("usuarios:login"), r["Location"])
        self.assertIn(self.client.get("/api/activos/").status_code, (401, 403))

    def test_todos_los_mantenedores_responden(self):
        self.client.force_login(self.admin)
        for slug, m in REGISTRO.items():
            r = self.client.get(reverse("crud_lista", args=[slug]))
            self.assertEqual(r.status_code, 200, slug)
            obj = m.get_queryset().first()
            if obj:
                self.assertEqual(self.client.get(reverse("crud_detalle", args=[slug, obj.pk])).status_code, 200, slug)
                if m.permite_editar:
                    self.assertEqual(self.client.get(reverse("crud_editar", args=[slug, obj.pk])).status_code, 200, slug)
            if m.permite_crear and not m.url_crear:
                self.assertEqual(self.client.get(reverse("crud_crear", args=[slug])).status_code, 200, slug)

    def test_crud_region(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("crud_crear", args=["regiones"]), {"codigo": "ZZ", "nombre": "Prueba", "orden": 99, "vigente": "on"})
        self.assertEqual(r.status_code, 302)
        reg = Region.objects.get(codigo="ZZ")
        self.client.post(reverse("crud_editar", args=["regiones", reg.pk]), {"codigo": "ZZ", "nombre": "Prueba 2", "orden": 99})
        reg.refresh_from_db()
        self.assertEqual(reg.nombre, "Prueba 2")
        self.assertFalse(reg.vigente)
        self.client.post(reverse("crud_eliminar", args=["regiones", reg.pk]))
        self.assertFalse(Region.objects.filter(codigo="ZZ").exists())

    def test_no_elimina_registro_en_uso(self):
        self.client.force_login(self.admin)
        temuco = Region.objects.get(codigo="IX")
        self.client.post(reverse("crud_eliminar", args=["regiones", temuco.pk]))
        self.assertTrue(Region.objects.filter(pk=temuco.pk).exists())

    def test_rol_consulta_no_puede_crear(self):
        self.client.force_login(User.objects.get(username="consulta"))
        self.assertEqual(self.client.get(reverse("crud_lista", args=["activos"])).status_code, 200)
        self.assertEqual(self.client.get(reverse("crud_crear", args=["activos"])).status_code, 403)
        self.assertEqual(self.client.get(reverse("prestamos:nuevo")).status_code, 403)
        self.assertEqual(self.client.post("/api/marcas/", {"nombre": "X"}).status_code, 403)

    def test_paginas_principales(self):
        self.client.force_login(self.admin)
        p = Prestamo.objects.first()
        urls = [reverse("dashboard"), reverse("mantenedores"), reverse("prestamos:nuevo"), reverse("alertas:lista"),
                p.get_absolute_url(), reverse("prestamos:devolver", args=[Prestamo.objects.filter(fecha_devolucion__isnull=True).first().pk]),
                Activo.objects.first().get_absolute_url(), self.c2.get_absolute_url(),
                Mantenimiento.objects.first().get_absolute_url(), "/admin/", "/api/",
                "/api/comunas/?ciudad=1", "/admin/prestamos/prestamo/%d/change/" % p.pk]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_flujo_web_prestamo(self):
        self.client.force_login(User.objects.get(username="bodega"))
        activo = self.disponibles()[0]
        r = self.client.post(reverse("prestamos:nuevo"), {
            "contratista": self.c3.pk, "responsable": self.c3.responsables.first().pk,
            "obra": Prestamo.objects.first().obra_id, "fecha_compromiso": (timezone.localdate() + timedelta(days=2)).isoformat(),
            "activos": [activo.pk], "firma": FIRMA,
        })
        self.assertEqual(r.status_code, 302)
        activo.refresh_from_db()
        self.assertEqual(activo.estado.codigo, "EN_USO")
