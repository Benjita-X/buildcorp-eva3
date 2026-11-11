# Registro de uso de Inteligencia Artificial

**Herramienta:** Claude (Anthropic), mediante Claude Code (app de escritorio).
**Fecha:** 04-11-2026
**Proyecto:** BuildCorp – Sistema de Alquiler y Control de Herramientas (Proyecto 4, EVA 3 Backend)

> Complete o ajuste esta bitácora con cualquier consulta adicional que haga durante la semana.

---

## Prompt 1 – Análisis del enunciado y requerimientos
**Consulta:** Se entregaron a la IA los documentos `EVA_3_Backend.docx`, `Proyectos_para_EVA_3_BCKEND.docx` y la planilla de
asignación de temas, indicando: *"me toca el tema 4 … cada tabla diferente, todo sistema de templates, todo tiene que estar
parametrizado: ciudad, comuna, región … hay que hacer un administrador para cada tabla, solo templates"*.

**Apoyo recibido:** identificación del caso BuildCorp y de los 4 requerimientos funcionales, cruce con la rúbrica
(PostgreSQL, Django Admin con filtros y templates, CRUD + reglas de negocio, seguridad/sesiones, despliegue EC2).

**Decisión propia:** mantener *además* el Django Admin personalizado, porque la rúbrica lo evalúa (criterio 2).

## Prompt 2 – Modelo de datos parametrizado
**Consulta:** diseñar los modelos para que estados, tipos, territorio (Región → Ciudad → Comuna) y reglas de negocio
estén en tablas y no en `choices` fijos.

**Apoyo recibido:** propuesta de apps (`parametros`, `inventario`, `contratistas`, `prestamos`, `mantenimiento`,
`alertas`), clase abstracta `ParametroCodificado` con `codigo` + `es_sistema`, tabla clave/valor `ParametroSistema`,
FK con `on_delete=PROTECT`.

## Prompt 3 – Mantenedor genérico por templates
**Consulta:** cómo hacer un administrador (CRUD) para cada tabla sin repetir una vista y un template por tabla.

**Apoyo recibido:** clase `Mantenedor` + registro (`core/crud.py`), vistas genéricas basadas en clases con
`PermissionRequiredMixin`, templates `crud_list/form/detail/confirm_delete.html` con búsqueda, filtros, orden y paginación.

## Prompt 4 – Reglas de negocio
**Consulta:** implementar préstamo/devolución con firma digital, trazabilidad, mantenimiento por horas o fechas,
morosidad y bloqueo automático.

**Apoyo recibido:** capa `services.py` con transacciones atómicas; firma con `<canvas>` → PNG base64; sobrescritura de
`Activo.save()` para registrar `MovimientoActivo`; comando `revisar_alertas`; cálculo de cobro con recargo parametrizable.

## Prompt 5 – Frontend responsivo y consumo asíncrono de la API
**Consulta:** estructura HTML/CSS con Bootstrap 5 y JS para selects encadenados Región/Ciudad/Comuna, filtro de
responsables por contratista y refresco del dashboard.

**Apoyo recibido:** `static/js/app.js` (fetch a la API DRF), `static/css/app.css`, personalización de `admin/base_site.html`.

## Prompt 6 – Seguridad y API REST
**Consulta:** autenticación, sesiones con expiración por inactividad, roles y permisos también en la API.

**Apoyo recibido:** `LoginRequiredMiddleware` (Django 5.1) con excepción para `/api/`, `DjangoModelPermissions` estricto
(exige `view_` en GET), grupos Administrador / Bodeguero / Encargado de Mantención / Consulta.

## Prompt 7 – Pruebas y despliegue en AWS EC2
**Consulta:** pruebas automáticas de las reglas y script de despliegue en EC2 con PostgreSQL.

**Apoyo recibido:** `core/tests.py` (20 pruebas), `deploy/setup_ec2.sh`, unidades systemd para Gunicorn y el timer de
alertas, configuración de Nginx, `.env.example`.

## Prompt 8 – Usuarios aparte y despliegue final (10-11-2026)
**Consulta:** *"tiene que quedar listo, con todo lo de la rúbrica, fiel a lo que me tocó, separar por usuario, todo en templates,
que haya Django Admin pero no dejarle todo junto"*, y desplegarlo en mi cuenta AWS.

**Apoyo recibido:** app `usuarios` separada (login/logout, cambio de clave, gestión de usuarios con rol mediante vistas
basadas en clases y templates propios; Django Admin solo para el administrador), 5 pruebas nuevas, ajuste del despliegue a
la receta del curso (Gunicorn con socket unix en `/home/ubuntu/apps/`, Nginx con `location /static/` y logs, permisos
`www-data`), creación de la instancia EC2 Ubuntu 22.04 t3.micro, Security Group (22 desde mi IP, 80, 443, ICMP) e IP elástica
desde AWS CloudShell, y verificación del sitio en la IP pública.

---

### Validación realizada por el alumno
- Ejecutar `python manage.py test` y revisar que todas las pruebas pasen.
- Probar en vivo: entrega con firma → devolución con daño → OT correctiva → completar OT.
- Verificar que un contratista moroso quede bloqueado y no aparezca en el formulario de entrega.
- Revisar cada mantenedor y el Django Admin con los distintos roles.
