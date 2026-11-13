# BERA — Conectadas para avanzar (Demostración Funcional)

Demostración funcional PWA (Progressive Web App) para mujeres de las **21 comunas de la Región de Ñuble, Chile**, que centraliza **Movilidad**, **Empleabilidad** y **Emprendimiento**.

> **Aviso permanente:** Demostración: no coordina viajes ni procesa pagos reales. Todos los perfiles, documentos, ubicaciones, notificaciones y pagos son simulados.

## Arquitectura breve
- **Backend:** FastAPI (Python 3.11) + Uvicorn, con validación de entradas (Pydantic), limitación de tasa por IP, cabeceras de seguridad, hashing PBKDF2-HMAC-SHA256, sesiones persistentes en servidor y control de permisos RBAC en cada endpoint.
- **Base de datos:** SQLite (`bera.db`) con 24 tablas relacionales (`users`, `sessions`, `companies`, `verifications`, `consents`, `drivers`, `vehicles`, `trusted_contacts`, `trip_requests`, `fare_proposals`, `trips`, `job_offers`, `job_applications`, `ventures`, `venture_items`, `favorites`, `conversations`, `messages`, `reviews`, `blocks`, `reports`, `ads`, `notifications`, `audit_logs`, `app_config`).
- **Frontend:** PWA responsive mobile-first en HTML5, CSS3 (paleta `#F7C8DA`, `#FFFFFF`, `#FFF7FB`, `#AD285F`, `#342630`) y JavaScript modular ES6 sin dependencias CDN externas, con `manifest.json` y `sw.js` (soporte offline). Incluye selector de **Sesión A / Sesión B** para probar flujos de dos personas en el mismo navegador.

## Ejecución local y despliegue
```bash
cd bera_app
cp .env.example .env
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```
Luego abre `http://localhost:8000` en tu navegador (o desde el celular en la misma red local) e instala como PWA si lo deseas.

### Respaldo y restauración
```bash
python3 backup_restore.py backup
python3 backup_restore.py restore backups/bera_backup_YYYYMMDD_HHMMSS.db
```

## Accesos de demostración (Clave general: `BeraDemo2026!`)
| Rol | Correo | Comuna |
| --- | --- | --- |
| Pasajera / Postulante | `pasajera@bera.cl` | Chillán |
| Conductora 1 (Aprobada) | `conductora@bera.cl` | Chillán |
| Conductora 2 (Aprobada) | `conductora2@bera.cl` | San Carlos |
| Postulante | `postulante@bera.cl` | Bulnes |
| Emprendedora (Aprobada) | `emprendedora@bera.cl` | Quillón |
| Representante Empresa | `empresa@bera.cl` | Chillán |
| Verificación rechazada | `rechazada@bera.cl` | Coihueco |
| Admin 1 (General `*`) | `admin1@bera.cl` | Chillán |
| Admin 2 (Identidad/Movilidad) | `admin2@bera.cl` | Chillán Viejo |
| Admin 3 (Empleos/Denuncias) | `admin3@bera.cl` | San Carlos |
| Admin 4 (Vitrina/Publicidad) | `admin4@bera.cl` | Bulnes |
