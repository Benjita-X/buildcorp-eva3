# BuildCorp · Sistema de Alquiler y Control de Herramientas

**Evaluación Parcial N°3 – Desarrollo Backend (INACAP) · Proyecto 4**
Alumno: Benjamín Kreps Bravo

> **Aplicación desplegada en AWS EC2:** http://16.59.68.35/
> **Django Admin:** http://16.59.68.35/admin/ · **API REST:** http://16.59.68.35/api/

---

## 1. Problema y solución

BuildCorp pierde maquinaria ligera y herramientas, cobra mal a los subcontratistas y sufre fallas imprevistas porque
no sabe dónde está cada activo ni cuándo mantenerlo. Este sistema centraliza:

| Requerimiento del caso | Cómo se resuelve |
|---|---|
| **Catálogo de activos con trazabilidad de estado** (Disponible, En Uso, Mantenimiento, Dado de Baja) | Modelo `Activo` + tabla `EstadoActivo` (parametrizada). Cada cambio de estado o bodega queda en `MovimientoActivo` automáticamente → **hoja de vida** del activo. Traslados entre bodegas de obra y baja con motivo. |
| **Entrega y devolución con firma digital del responsable de obra** | Flujo `/prestamos/nuevo/` y `/prestamos/<id>/devolver/` con firma dibujada en `<canvas>` (PNG base64), validada también en el servidor. Comprobante imprimible con ambas firmas. |
| **Mantenimiento preventivo por uso o fechas límite** | `PlanMantenimiento` (cada N horas y/o cada N días). Las horas de uso informadas en cada devolución se suman al horómetro del activo. Al vencer un plan se genera la **OT automáticamente**; una devolución con daño genera una **OT correctiva**. |
| **Alertas por morosidad y bloqueo automático de contratistas morosos** | Servicio `alertas/services.py`: préstamo vencido → estado *Atrasado* + alerta; si el contratista llega al máximo de préstamos morosos (parámetro) se **bloquea automáticamente** y no puede retirar más herramientas. Se desbloquea solo al regularizar. La revisión se ejecuta al abrir el dashboard o las alertas. |
| Cobros exactos | Tarifa diaria congelada al momento del préstamo × días facturables (incluye los días de atraso). |

## 2. Todo parametrizado

No hay valores en duro: cada tabla de parámetros tiene su propio **mantenedor por templates** (listar, buscar, filtrar,
ordenar, crear, editar, eliminar) y también está registrada en Django Admin.

- **Territorio:** Región → Ciudad → Comuna (selects encadenados que consumen la API REST).
- **Catálogos:** Categorías de activo, Marcas, Cargos.
- **Estados y tipos:** Estados de activo, de préstamo, de mantenimiento, tipos de mantenimiento, tipos de alerta, condiciones de devolución.
- **Reglas de negocio** (`ParametroSistema`): días de gracia, préstamos morosos para bloqueo, **bloqueo automático Sí/No** (por defecto Sí; el bloqueo manual siempre está disponible), días/horas de aviso de mantención, aviso de vencimiento.

Los registros que usa la lógica (ej. estado `DISPONIBLE`) se marcan como **de sistema**: se puede cambiar su nombre/color,
pero no su código ni eliminarlos. Ningún registro en uso se puede borrar (FK `PROTECT`), se marca como *no vigente*.

### Motor de mantenedores (templates)
`core/crud.py` define la clase `Mantenedor`. Cada app registra sus tablas en su `mantenedores.py`, por ejemplo:

```python
registrar(Mantenedor(
    Comuna, "comunas", "Territorio", "bi-geo-alt",
    columnas=["nombre", "ciudad", "ciudad__region", "vigente"],
    busqueda=["nombre", "ciudad__nombre"], filtros=["ciudad", "vigente"],
))
```

Con eso se generan las pantallas `/m/comunas/`, `/m/comunas/nuevo/`, `/m/comunas/<id>/editar/`… usando los templates
`templates/core/crud_*.html`, respetando los permisos `view/add/change/delete` del rol.

## 3. Arquitectura (modelo 4+1)

- **Vista lógica:** apps `parametros`, `inventario` (Obra, Bodega, Activo, MovimientoActivo), `contratistas`
  (Contratista, ResponsableObra), `prestamos` (Prestamo, DetallePrestamo), `mantenimiento` (PlanMantenimiento,
  Mantenimiento), `alertas` (Alerta) y `core` (mantenedores, dashboard, API, comandos).
- **Vista de procesos:** Entrega → (activos *En Uso*) → Devolución con horas y condición → (activo *Disponible* o
  *Mantenimiento* + OT) → revisión periódica de morosidad → bloqueo/desbloqueo automático.
- **Vista de desarrollo:** reglas de negocio en `services.py` de cada app (las vistas solo orquestan), templates
  Bootstrap 5, API DRF con `ModelViewSet` por tabla, pruebas en `core/tests.py`.
- **Vista física:** una instancia **EC2** con Nginx (:80) → socket unix → Gunicorn → Django → **PostgreSQL** local.
- **Escenarios:** registrar entrega con firma, devolver con daño, contratista moroso bloqueado, mantención por horas.

## 4. Seguridad, sesiones y roles

- Todas las vistas exigen sesión (`LoginRequiredMiddleware`); la API usa sesión o Basic Auth.
- Sesión expira tras **30 min de inactividad** (`SESSION_COOKIE_AGE`, `SESSION_SAVE_EVERY_REQUEST`), cookies `HttpOnly`, CSRF.
- Permisos por modelo de Django en vistas, mantenedores y API (`core/permissions.py` exige `view_` también para GET).
- Roles (grupos) creados por `cargar_datos_iniciales`:

| Rol | Puede |
|---|---|
| Administrador | Todo + Django Admin |
| Bodeguero | Ver todo; registrar entregas/devoluciones, activos, bodegas, contratistas, responsables; resolver alertas |
| Encargado de Mantención | Ver todo; planes y órdenes de mantenimiento; resolver alertas |
| Consulta | Solo lectura |

Usuarios demo: `admin`, `bodega`, `mantencion`, `consulta` (contraseña = `DEMO_PASSWORD` del `.env`).

**Usuarios aparte (app `usuarios`):** login, logout y cambio de contraseña con templates propios, y gestión de usuarios
(listar, crear con rol, editar, activar/desactivar, asignar contraseña) en `/usuarios/`, solo para el rol Administrador.
El **Django Admin** (`/admin/`) queda únicamente para el administrador (`is_staff`); el resto de los roles trabaja
solo con las pantallas propias.

## 5. Ejecución local

```bash
python -m venv venv
venv\Scripts\activate            # Linux/Mac: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env           # Linux/Mac: cp .env.example .env  -> completar datos de PostgreSQL
python manage.py migrate
python manage.py cargar_datos_iniciales --demo
python manage.py runserver
```

Para una prueba rápida sin PostgreSQL se puede poner `DB_ENGINE=sqlite` en el `.env` (solo desarrollo).
Pruebas automáticas: `python manage.py test` (pruebas de reglas de negocio, permisos, usuarios y mantenedores).

## 6. Despliegue en AWS EC2 (siguiendo la receta del curso)

**ETAPA 1 – Instancia:** Ubuntu Server 22.04, t3.micro, par de claves, VPC por defecto con IP pública.
*Security Group:* SSH 22 desde mi IP, HTTP 80 para todos, HTTPS 443, ICMP (ping). **IP elástica** asociada.

**ETAPA 2 – Conexión SSH desde Windows** (proteger la clave con `icacls`):
```powershell
icacls C:\AWS_KEYS\claves-buildcorp.pem /inheritance:r /grant:r "$($env:USERNAME):(R)"
ssh -i C:\AWS_KEYS\claves-buildcorp.pem ubuntu@16.59.68.35
```

**ETAPA 3 – Paquetes:**
```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv nginx git postgresql postgresql-contrib
```

**ETAPA 4 – Proyecto, base de datos PostgreSQL y prueba:**
```bash
sudo -u postgres psql -c "CREATE USER buildcorp WITH PASSWORD '...';"
sudo -u postgres createdb -O buildcorp buildcorp
mkdir -p ~/apps && cd ~/apps
git clone https://github.com/Benjita-X/buildcorp-eva3.git buildcorp && cd buildcorp
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env && nano .env      # SECRET_KEY, DEBUG=False, IP, datos de PostgreSQL
python manage.py migrate
python manage.py collectstatic
python manage.py cargar_datos_iniciales --demo
```

**ETAPA 5 – Gunicorn como servicio systemd** (3 workers, socket unix `/home/ubuntu/apps/buildcorp.sock`):
el contenido está en [`deploy/buildcorp.service`](deploy/buildcorp.service) → copiar a `/etc/systemd/system/buildcorp.service`.

**ETAPA 6 – Nginx como proxy inverso** (con `location /static/` y logs):
el contenido está en [`deploy/nginx_buildcorp.conf`](deploy/nginx_buildcorp.conf) → copiar a `/etc/nginx/sites-available/buildcorp`,
enlazar en `sites-enabled` y borrar `/etc/nginx/sites-enabled/default`.

**Permisos** (para que `www-data`, el usuario de Nginx, llegue al socket):
```bash
sudo usermod -aG www-data ubuntu
sudo chown ubuntu:www-data /home/ubuntu /home/ubuntu/apps /home/ubuntu/apps/buildcorp
chmod 750 /home/ubuntu /home/ubuntu/apps /home/ubuntu/apps/buildcorp
```

**ETAPA 8 – Recargar y probar:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now buildcorp
sudo nginx -t && sudo systemctl restart nginx
```
Probar http://16.59.68.35/ , http://16.59.68.35/api/ y http://16.59.68.35/admin/

Comandos útiles: `sudo systemctl status buildcorp nginx` · `sudo journalctl -u buildcorp -n 50` · `sudo tail /var/log/nginx/buildcorp_error.log`

## 7. Endpoints principales

| URL | Descripción |
|---|---|
| `/` | Dashboard (préstamos, morosos, bloqueados, mantenciones y alertas) |
| `/prestamos/nuevo/` | Entrega con firma digital |
| `/prestamos/<id>/` · `/prestamos/<id>/devolver/` | Comprobante y devolución |
| `/inventario/activos/<id>/` | Hoja de vida del activo (trazabilidad, préstamos, OTs) |
| `/contratistas/<id>/` | Ficha del contratista, bloqueo/desbloqueo |
| `/mantenimiento/ot/<id>/` | Orden de trabajo: iniciar / completar / cancelar |
| `/alertas/` | Alertas pendientes/resueltas y revisión manual |
| `/mantenedores/` · `/m/<tabla>/` | Mantenedores por template de cada tabla |
| `/usuarios/` | Gestión de usuarios y roles (templates propios); `/usuarios/login/` |
| `/api/` | API REST navegable (DRF) — un endpoint por tabla |
| `/admin/` | Django Admin personalizado |

