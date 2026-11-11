from django.core.management.base import BaseCommand

from alertas.services import ejecutar_revisiones


class Command(BaseCommand):
    help = "Revisa morosidad (bloqueo automático), préstamos por vencer y mantenciones. Programar con cron/systemd."

    def handle(self, *args, **opts):
        r = ejecutar_revisiones()
        self.stdout.write(self.style.SUCCESS(" | ".join(f"{k}: {v}" for k, v in r.items())))
