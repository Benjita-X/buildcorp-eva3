# =============================================================================
# Middleware de seguridad: obliga a iniciar sesión para ver cualquier página.
# Un middleware revisa CADA petición antes de que llegue a la vista.
# =============================================================================
from django.contrib.auth.middleware import LoginRequiredMiddleware


# Hereda del LoginRequiredMiddleware de Django (redirige al login si no hay sesión)
class LoginObligatorioMiddleware(LoginRequiredMiddleware):
    """
    Exige sesión iniciada en todas las vistas HTML.
    La API (/api/) queda fuera porque DRF hace su propia autenticación
    (sesión o Basic Auth) y responde 401/403 en JSON en vez de redirigir.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        # Si la dirección empieza con /api/, deja pasar: la API revisa el login por su cuenta
        if request.path.startswith("/api/"):
            return None
        # Para todo lo demás: si no hay sesión, manda al login
        return super().process_view(request, view_func, view_args, view_kwargs)
