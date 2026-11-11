#!/usr/bin/env python
# =============================================================================
# manage.py = el "control remoto" del proyecto Django.
# Ejemplos: python manage.py runserver / migrate / makemigrations / test
# =============================================================================
import os
import sys


def main():
    # Indica qué archivo de configuración usar (config/settings.py)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    # Ejecuta el comando que se escribió en la terminal
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
