#!/usr/bin/env bash
# =============================================================================
# Despliegue de BuildCorp en EC2 Ubuntu Server 22.04 siguiendo la receta:
#   Nginx (:80) --proxy--> socket unix --> Gunicorn (3 workers) --> Django --> PostgreSQL
#
# Uso (en la instancia, como usuario ubuntu):
#   mkdir -p ~/apps && cd ~/apps
#   git clone https://github.com/Benjita-X/buildcorp-eva3.git buildcorp && cd buildcorp
#   bash deploy/setup_ec2.sh
# Si no existe .env, el script lo crea con claves aleatorias y la IP pública.
# =============================================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"     # /home/ubuntu/apps/buildcorp
APPS_DIR="$(dirname "$APP_DIR")"                # /home/ubuntu/apps
SOCK="$APPS_DIR/buildcorp.sock"                 # /home/ubuntu/apps/buildcorp.sock
cd "$APP_DIR"

echo ">> ETAPA 3: paquetes del sistema"
sudo apt-get update -y
sudo DEBIAN_FRONTEND=noninteractive apt-get upgrade -y
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-pip python3-venv nginx git postgresql postgresql-contrib

IP="$(curl -s --max-time 3 http://checkip.amazonaws.com || echo 127.0.0.1)"
if [ ! -f .env ]; then
  echo ">> Creando .env (claves aleatorias, DEBUG=False)"
  aleatorio() { python3 -c "import secrets; print(secrets.token_urlsafe($1))"; }
  cat > .env <<EOF
DJANGO_SECRET_KEY=$(aleatorio 50)
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=${IP},localhost,127.0.0.1
DJANGO_CSRF_TRUSTED_ORIGINS=http://${IP}
DB_ENGINE=postgres
DB_NAME=buildcorp
DB_USER=buildcorp
DB_PASSWORD=$(aleatorio 24)
DB_HOST=localhost
DB_PORT=5432
SESSION_COOKIE_AGE=1800
USE_HTTPS=False
DEMO_PASSWORD=$(aleatorio 9)
EOF
  chmod 600 .env
fi
leer_env() { grep -E "^$1=" .env | head -1 | cut -d= -f2-; }
DB_NAME="$(leer_env DB_NAME)"; DB_USER="$(leer_env DB_USER)"; DB_PASSWORD="$(leer_env DB_PASSWORD)"

echo ">> Base de datos PostgreSQL"
sudo systemctl enable --now postgresql
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$ BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASSWORD}';
  ELSE
    ALTER ROLE ${DB_USER} WITH PASSWORD '${DB_PASSWORD}';
  END IF;
END \$\$;
SQL
sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" | grep -q 1 \
  || sudo -u postgres createdb -O "${DB_USER}" "${DB_NAME}"

echo ">> ETAPA 4: entorno virtual, dependencias, migraciones y estáticos"
python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt
./venv/bin/python manage.py migrate --noinput
./venv/bin/python manage.py collectstatic --noinput
./venv/bin/python manage.py cargar_datos_iniciales --demo

echo ">> Permisos: www-data (Nginx) debe poder llegar al socket y a los estáticos"
sudo usermod -aG www-data ubuntu
sudo chown ubuntu:www-data "$HOME" "$APPS_DIR" "$APP_DIR"
chmod 750 "$HOME" "$APPS_DIR" "$APP_DIR"
sudo chown -R ubuntu:www-data "$APP_DIR/staticfiles"
find "$APP_DIR/staticfiles" -type d -exec chmod 750 {} +
find "$APP_DIR/staticfiles" -type f -exec chmod 640 {} +

echo ">> ETAPA 5: Gunicorn como servicio systemd (socket $SOCK)"
for f in buildcorp.service buildcorp-alertas.service buildcorp-alertas.timer; do
  sed -e "s#__APP_DIR__#${APP_DIR}#g" -e "s#__SOCK__#${SOCK}#g" "deploy/$f" | sudo tee "/etc/systemd/system/$f" >/dev/null
done

echo ">> ETAPA 6: Nginx como proxy inverso"
sed -e "s#__APP_DIR__#${APP_DIR}#g" -e "s#__SOCK__#${SOCK}#g" deploy/nginx_buildcorp.conf \
  | sudo tee /etc/nginx/sites-available/buildcorp >/dev/null
sudo ln -sf /etc/nginx/sites-available/buildcorp /etc/nginx/sites-enabled/buildcorp
sudo rm -f /etc/nginx/sites-enabled/default      # si no, aparece "Welcome to nginx"
sudo nginx -t

echo ">> ETAPA 8: recargar y reiniciar servicios"
sudo systemctl daemon-reload
sudo systemctl enable --now buildcorp.service buildcorp-alertas.timer
sudo systemctl restart buildcorp.service
sudo systemctl restart nginx
sleep 2
ls -l "$SOCK"
curl -s -o /dev/null -w "HTTP local: %{http_code}\n" http://localhost/usuarios/login/

echo ""
echo "============================================================"
echo " Listo:  http://${IP}/        Admin: http://${IP}/admin/"
echo " API:    http://${IP}/api/"
echo "============================================================"
