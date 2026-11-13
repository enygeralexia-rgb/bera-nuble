# Guía para las cuatro administradoras de BERA

La plataforma cuenta con **4 cuentas individuales de administración** con permisos configurables en servidor y registro obligatorio de auditoría (`admin_user_id`, fecha y motivo):

1. **`admin1@bera.cl` — Directora General (`*`)**
   - Acceso completo a indicadores, auditoría, configuraciones y todas las colas de moderación.
2. **`admin2@bera.cl` — Moderadora de Identidad y Movilidad (`verifications`, `drivers`, `appeals`, `indicators`)**
   - Revisa verificaciones simuladas de identidad, licencias de conductoras y vehículos, apelaciones de elegibilidad y suspensiones de cuentas.
3. **`admin3@bera.cl` — Moderadora de Empleos y Empresas (`jobs`, `companies`, `reports`, `indicators`)**
   - Aprueba o rechaza ofertas laborales antes de su publicación y resuelve denuncias de posibles estafas o contenido engañoso.
4. **`admin4@bera.cl` — Moderadora de Emprendimientos y Publicidad (`ventures`, `ads`, `reports`, `indicators`)**
   - Modera emprendimientos nuevos o editados (cambios sensibles vuelven automáticamente a `en revisión`), gestiona anuncios ficticios y atiende denuncias.

## Reglas operativas en la demostración
- **Prevención de resoluciones contradictorias:** Si una verificación ya fue marcada como `aprobada` o `rechazada` por otra administradora, el sistema bloquea (`HTTP 409`) un cambio contradictorio directo y remite al historial de auditoría.
- **Indicadores de demostración:** Todos los contadores del panel están etiquetados como datos ficticios de demostración; no confunden contactos comerciales con ventas ni postulaciones con contrataciones.
- **Producción:** En entorno productivo se debe habilitar autenticación reforzada (2FA/MFA) y restricción por red/IP para estas cuentas.
