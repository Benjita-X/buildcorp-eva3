from django.contrib.auth.middleware import LoginRequiredMiddleware


class LoginObligatorioMiddleware(LoginRequiredMiddleware):
    """
    Exige sesión iniciada en todas las vistas HTML.
    La API (/api/) queda fuera porque DRF hace su propia autenticación
    (sesión o Basic Auth) y responde 401/403 en JSON en vez de redirigir.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if request.path.startswith("/api/"):
            return None
        return super().process_view(request, view_func, view_args, view_kwargs)
