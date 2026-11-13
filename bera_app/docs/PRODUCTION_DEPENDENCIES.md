# Funciones reales, simuladas, pendientes y dependencias de producción

## 1. Estado actual de funcionalidades
- **Reales en la demostración:**
  - Registro, login, sesiones en servidor, hashing PBKDF2-HMAC-SHA256, validación de permisos RBAC y restricciones de invitadas.
  - Persistencia en SQLite (24 tablas) con respaldo y restauración.
  - Catálogo verificado de las 21 comunas de la Región de Ñuble.
  - Flujos completos de solicitud de viaje, negociación de tarifa con contraofertas, prevención de doble asignación y conflictos de horario, enlaces compartidos temporales revocables, empleos con aislamiento por empleadora, emprendimientos con re-moderación, chat interno, bloqueos, denuncias, auditoría y PWA instalable.
- **Simuladas en la demostración:**
  - Verificación de correo, recuperación de contraseña y verificación de identidad/cédula/licencia ("Verificación simulada").
  - Cálculo de distancia/duración entre cabeceras comunales y barra de progreso de viaje (sin GPS en tiempo real).
  - Pagos (`efectivo`, `transferencia`, `pago_bera` con distinción entre "pago declarado" y "confirmado simulado").
  - Notificaciones internas, contactos de confianza, WhatsApp autorizado y botón de ayuda (flujo de prueba sin alertas externas).
  - Publicidad e indicadores de administración.
- **Pendientes para versión operativa:**
  - Definición legal y operativa de edad mínima, acompañamiento y autorización para pasajeras menores de edad (contratación autónoma deshabilitada por defecto).
  - Reglas comerciales y comisiones de movilidad (actualmente configurables en `app_config`).

## 2. Dependencias necesarias para producción
1. **Verificación de identidad y biometría:** Proveedor especializado de validación de cédula chilena (Registro Civil / KYC) y prueba de vida facial con minimización de datos sensibles y revisión humana.
2. **Mapas y geolocalización:** API de mapas, geocodificación y rutas en tiempo real dentro de Ñuble.
3. **Correo y teléfono:** Proveedor SMTP/transaccional (SES, SendGrid o Postmark) y gateway SMS/OTP para verificación de teléfono.
4. **Pagos:** Pasarela de pagos chilena (Webpay/Transbank, MercadoPago o Khipu) con cumplimiento PCI-DSS.
5. **Notificaciones:** Web Push / FCM para alertas en tiempo real.
6. **Alojamiento y base de datos:** Servidor HTTPS con PostgreSQL administrado, copias automáticas y secretos en gestor seguro.
7. **Requisitos de operación del transporte:** Cumplimiento normativo del Ministerio de Transportes y Telecomunicaciones (MTT) de Chile, seguros, licencias profesionales si aplica y revisión legal de transporte privado de pasajeras.
