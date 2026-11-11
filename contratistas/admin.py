from django.contrib import admin, messages

from core.admin_utils import badge

from .models import Contratista, ResponsableObra


class ResponsableInline(admin.TabularInline):
    model = ResponsableObra
    extra = 0
    fields = ["rut", "nombre", "cargo", "telefono", "email", "vigente"]


@admin.register(Contratista)
class ContratistaAdmin(admin.ModelAdmin):
    list_display = ["rut", "razon_social", "comuna", "telefono", "estado_bloqueo", "vigente"]
    list_filter = ["bloqueado", "bloqueo_automatico", "vigente", "comuna__ciudad__region"]
    search_fields = ["rut", "razon_social", "nombre_fantasia", "email"]
    autocomplete_fields = ["comuna"]
    readonly_fields = ["bloqueado", "bloqueo_automatico", "motivo_bloqueo", "fecha_bloqueo", "creado"]
    fieldsets = [
        ("Datos tributarios", {"fields": [("rut", "razon_social"), ("nombre_fantasia", "giro")]}),
        ("Contacto", {"fields": [("direccion", "comuna"), ("telefono", "email"), "vigente"]}),
        ("Bloqueo por morosidad", {"fields": [("bloqueado", "bloqueo_automatico"), "motivo_bloqueo", "fecha_bloqueo"]}),
    ]
    inlines = [ResponsableInline]
    actions = ["accion_bloquear", "accion_desbloquear"]

    @admin.display(description="Estado", ordering="bloqueado")
    def estado_bloqueo(self, obj):
        if obj.bloqueado:
            return badge("Bloqueado (auto)" if obj.bloqueo_automatico else "Bloqueado", "danger")
        return badge("Habilitado", "success")

    @admin.action(description="Bloquear contratistas seleccionados")
    def accion_bloquear(self, request, queryset):
        for c in queryset:
            c.bloquear(f"Bloqueo manual desde Admin por {request.user.username}")
        self.message_user(request, f"{queryset.count()} contratista(s) bloqueado(s).", messages.WARNING)

    @admin.action(description="Desbloquear contratistas seleccionados")
    def accion_desbloquear(self, request, queryset):
        for c in queryset:
            c.desbloquear()
        self.message_user(request, f"{queryset.count()} contratista(s) desbloqueado(s).", messages.SUCCESS)


@admin.register(ResponsableObra)
class ResponsableAdmin(admin.ModelAdmin):
    list_display = ["nombre", "rut", "contratista", "cargo", "telefono", "vigente"]
    list_filter = ["cargo", "vigente"]
    search_fields = ["nombre", "rut", "contratista__razon_social"]
    autocomplete_fields = ["contratista"]
