import io

from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse


class GestionUsuariosTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("cargar_datos_iniciales", "--demo", stdout=io.StringIO())

    def setUp(self):
        self.admin = User.objects.get(username="admin")

    def test_login_y_logout_con_templates_propios(self):
        r = self.client.get(reverse("usuarios:login"))
        self.assertTemplateUsed(r, "usuarios/login.html")
        self.client.force_login(self.admin)
        self.assertEqual(self.client.post(reverse("usuarios:logout")).status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard")).status_code, 302)

    def test_administrador_crea_usuario_con_rol(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("usuarios:crear"), {
            "username": "nuevo", "first_name": "Nuevo", "last_name": "Usuario", "email": "n@buildcorp.cl",
            "rol": Group.objects.get(name="Bodeguero").pk,
            "password1": "ClaveSegura.2026", "password2": "ClaveSegura.2026",
        })
        self.assertEqual(r.status_code, 302)
        u = User.objects.get(username="nuevo")
        self.assertTrue(u.check_password("ClaveSegura.2026"))
        self.assertEqual(list(u.groups.values_list("name", flat=True)), ["Bodeguero"])
        self.assertTrue(u.has_perm("prestamos.add_prestamo"))
        self.assertFalse(u.is_staff, "Los usuarios creados no entran al Django Admin")

    def test_roles_no_administradores_no_gestionan_usuarios(self):
        for nombre in ("bodega", "mantencion", "consulta"):
            self.client.force_login(User.objects.get(username=nombre))
            self.assertEqual(self.client.get(reverse("usuarios:lista")).status_code, 403, nombre)
            self.assertEqual(self.client.get(reverse("usuarios:crear")).status_code, 403, nombre)
            self.assertEqual(self.client.get("/admin/").status_code, 302, nombre)  # admin solo para staff

    def test_cambiar_mi_clave(self):
        u = User.objects.get(username="consulta")
        u.set_password("Vieja.Clave1")
        u.save()
        self.client.force_login(u)
        r = self.client.post(reverse("usuarios:mi_clave"), {
            "old_password": "Vieja.Clave1", "new_password1": "Nueva.Clave2026", "new_password2": "Nueva.Clave2026",
        })
        self.assertEqual(r.status_code, 302)
        u.refresh_from_db()
        self.assertTrue(u.check_password("Nueva.Clave2026"))

    def test_no_puede_desactivarse_a_si_mismo(self):
        Group.objects.get(name="Administrador").user_set.add(self.admin)
        self.client.force_login(self.admin)
        self.client.post(reverse("usuarios:editar", args=[self.admin.pk]), {
            "first_name": "Ana", "last_name": "Admin", "email": "a@b.cl", "rol": Group.objects.get(name="Administrador").pk,
        })
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
