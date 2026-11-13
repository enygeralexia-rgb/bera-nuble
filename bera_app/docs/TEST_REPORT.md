# Reporte Breve de Pruebas de Aceptación — BERA

**Ejecución:** `python3 tests/test_acceptance.py` (sobre base de datos SQLite aislada y limpia).
**Resultado:** **APROBADO (100% de los casos verificados sin errores)**.

## Cobertura verificada
1. **Salud, PWA y catálogo territorial:** Endpoint `/api/health`, `manifest.json`, `sw.js` y catálogo exacto de las 21 comunas de la Región de Ñuble.
2. **Restricciones de invitadas:** Lectura pública permitida (`GET /api/jobs`); creación de viajes y postulaciones bloqueadas (`401`).
3. **Registro y edad mínima:** Bloqueo de registro autónomo para menores de 18 años (`403`) y alta exitosa para mayores de 18 en comunas de Ñuble (`200`).
4. **Menores en movilidad:** Bloqueo explícito de contratación autónoma por menor (`403`) y soporte de visualización del flujo propuesto adulta responsable -> menor acompañada.
5. **Negociación y prevención de doble asignación:** Propuesta, contraoferta, aceptación bilateral con cierre automático de solicitud y bloqueo de confirmación duplicada (`409`).
6. **Conflictos de horario en viajes programados:** Bloqueo (`409`) cuando una conductora intenta aceptar otro viaje dentro de una ventana de 60 minutos.
7. **Estados de viaje, pagos y enlaces compartidos:** Avance de etapas, declaración y confirmación simulada de pago, creación y revocación de enlace compartido (`410` tras revocar).
8. **Empleabilidad y privacidad de postulantes:** Aislamiento estricto por empleadora (`403` al intentar consultar postulaciones de otra oferta).
9. **Emprendimientos:** Edición de campos sensibles devuelve la publicación a estado `en revisión`.
10. **Administración y trazabilidad:** Permisos diferenciados entre las 4 administradoras (`403` fuera de ámbito) y prevención de resoluciones contradictorias (`409`).
11. **Mensajería y bloqueo:** Bloqueo entre usuarias impide nuevos contactos (`403`/`404`).
