"""
Datos iniciales ficticios para la demostración funcional de BERA (Región de Ñuble).
Todos los perfiles, documentos, patentes, teléfonos y montos son ficticios.
"""
import json
from datetime import datetime, timedelta, timezone
from .database import db_session
from .security import hash_password, now_iso


def _dt_offset(hours: int = 0, days: int = 0) -> str:
    return (
        (datetime.now(timezone.utc) + timedelta(hours=hours, days=days))
        .replace(microsecond=0)
        .isoformat()
    )


def seed_database(db_path: str = None, force: bool = False):
    with db_session(db_path) as conn:
        existing = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        if existing > 0 and not force:
            return

        if force:
            for tbl in [
                "audit_logs", "notifications", "ads", "reports", "blocks", "reviews",
                "messages", "conversations", "favorites", "venture_items", "ventures",
                "job_applications", "job_offers", "trips", "fare_proposals", "trip_requests",
                "trusted_contacts", "vehicles", "drivers", "consents", "verifications",
                "companies", "sessions", "users", "app_config",
            ]:
                conn.execute(f"DELETE FROM {tbl}")

        pw = hash_password("BeraDemo2026!")
        created = now_iso()

        users = [
            # 1: Pasajera
            ("pasajera@bera.cl", pw, "Camila Riquelme (Demo)", "Chillán", "+56 9 0000 1001", 1996, 1,
             "utilizar servicios", '["pasajera", "postulante"]', None, "[]", 1, "ninguna", "", "activa", 1,
             "Técnica en Administración con experiencia en atención al cliente en Chillán.", "Atención al cliente, Excel básico, Caja", "#AD285F"),
            # 2: Conductora 1
            ("conductora@bera.cl", pw, "Valentina Muñoz (Demo)", "Chillán", "+56 9 0000 1002", 1991, 1,
             "ambas", '["pasajera", "conductora"]', None, "[]", 1, "ninguna", "", "activa", 1,
             "Conductora verificada en Chillán y alrededores.", "Conducción defensiva, Primeros auxilios", "#8E1D4B"),
            # 3: Conductora 2
            ("conductora2@bera.cl", pw, "Francisca Soto (Demo)", "San Carlos", "+56 9 0000 1003", 1989, 1,
             "ofrecer servicios", '["conductora"]', None, "[]", 1, "ninguna", "", "activa", 1,
             "Conductora en Punilla y Diguillín.", "Traslados interurbanos Ñuble", "#7A2048"),
            # 4: Postulante
            ("postulante@bera.cl", pw, "Daniela Paredes (Demo)", "Bulnes", "+56 9 0000 1004", 2001, 1,
             "utilizar servicios", '["pasajera", "postulante"]', None, "[]", 1, "ninguna", "", "activa", 1,
             "Egresada de Contabilidad General buscando primera oportunidad part-time o teletrabajo.", "Contabilidad, Facturación, Office", "#B83B6E"),
            # 5: Emprendedora
            ("emprendedora@bera.cl", pw, "Javiera Contreras (Demo)", "Quillón", "+56 9 0000 1005", 1994, 1,
             "ambas", '["pasajera", "emprendedora"]', None, "[]", 1, "ninguna", "", "activa", 1,
             "Creadora de cosmética natural con frutos de Quillón.", "Cosmética artesanal, Redes sociales", "#9D2456"),
            # 6: Representante de empresa
            ("empresa@bera.cl", pw, "Carolina Lagos (Demo)", "Chillán", "+56 9 0000 1006", 1985, 1,
             "ofrecer servicios", '["empresa"]', None, "[]", 1, "ninguna", "", "activa", 1,
             "Jefa de Personas en AgroFrut Ñuble SpA (empresa ficticia).", "Gestión de talento", "#6C1D45"),
            # 7: Cuenta con verificación rechazada (para probar corrección y apelación)
            ("rechazada@bera.cl", pw, "Sofía Herrera (Demo)", "Coihueco", "+56 9 0000 1007", 1998, 1,
             "ofrecer servicios", '["pasajera", "emprendedora"]', None, "[]", 1, "pendiente",
             "Solicito revisión manual de mi documento simulado porque la imagen anterior salió borrosa.", "activa", 1,
             "Repostera artesanal en Coihueco.", "Repostería", "#C24E7E"),
            # 8..11: 4 cuentas de administración individuales
            ("admin1@bera.cl", pw, "Elena Morales (Admin 1 - General)", "Chillán", "+56 9 0000 9001", 1984, 1,
             "ambas", '["admin"]', "admin_1", '["*"]', 1, "ninguna", "", "activa", 1, "", "", "#342630"),
            ("admin2@bera.cl", pw, "Patricia Vera (Admin 2 - Identidad)", "Chillán Viejo", "+56 9 0000 9002", 1988, 1,
             "ambas", '["admin"]', "admin_2", '["verifications", "drivers", "appeals", "indicators"]', 1, "ninguna", "", "activa", 1, "", "", "#4A3342"),
            ("admin3@bera.cl", pw, "Lorena Díaz (Admin 3 - Empleos)", "San Carlos", "+56 9 0000 9003", 1990, 1,
             "ambas", '["admin"]', "admin_3", '["jobs", "companies", "reports", "indicators"]', 1, "ninguna", "", "activa", 1, "", "", "#5E2B45"),
            ("admin4@bera.cl", pw, "Marta Fuentes (Admin 4 - Comunidad)", "Bulnes", "+56 9 0000 9004", 1987, 1,
             "ambas", '["admin"]', "admin_4", '["ventures", "ads", "reports", "indicators"]', 1, "ninguna", "", "activa", 1, "", "", "#75254C"),
        ]

        for u in users:
            conn.execute(
                """
                INSERT INTO users (
                    email, password_hash, full_name, comuna, phone_simulated, birth_year, is_adult,
                    intent, roles_json, admin_level, admin_permissions_json, eligibility_declared,
                    eligibility_appeal_status, eligibility_appeal_reason, account_status, email_verified,
                    cv_summary, cv_skills, avatar_color, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*u, created),
            )

        # Empresa ficticia (representada por user_id=6)
        conn.execute(
            """
            INSERT INTO companies (representative_user_id, name, rut_simulated, rubro, comuna, authorization_status, created_at)
            VALUES (6, 'AgroFrut Ñuble SpA (Ficticia)', '76.000.123-K (Simulado)', 'Agroindustria y Alimentos', 'Chillán', 'aprobada', ?)
            """,
            (created,),
        )

        # Verificaciones simuladas (incluyendo aprobada, pendiente, en revisión, rechazada, vencida)
        verifs = [
            (2, "conductora", "aprobada", "Cédula + Licencia Clase B (Simulada)", "SIM-DOC-2002", "LIC-B-SIM-881", "3 años conduciendo en Ñuble", 1, 9, "Documentación ficticia completa y vigente.", created),
            (3, "conductora", "aprobada", "Cédula + Licencia Clase B (Simulada)", "SIM-DOC-2003", "LIC-B-SIM-992", "5 años en rutas provinciales", 1, 9, "Aprobada en demostración.", created),
            (5, "emprendedora", "aprobada", "Cédula + Inicio actividades (Simulado)", "SIM-DOC-2005", "", "Emprendimiento local desde 2024", 1, 8, "Verificación aprobada.", created),
            (6, "empresa", "aprobada", "Cédula representante + Poder (Simulado)", "SIM-DOC-2006", "", "Representante autorizada AgroFrut Ñuble", 1, 10, "Entidad y representante aprobadas.", created),
            (7, "emprendedora", "rechazada", "Cédula (Simulada)", "SIM-DOC-2007", "", "", 1, 9, "Documento simulado ilegible; puede corregir y reenviar.", created),
            (1, "identidad", "en revisión", "Cédula (Simulada)", "SIM-DOC-2001", "", "", 1, None, "", created),
            (4, "identidad", "pendiente", "Cédula (Simulada)", "SIM-DOC-2004", "", "", 1, None, "", created),
            (3, "identidad", "vencida", "Cédula anterior (Simulada)", "SIM-DOC-2003-OLD", "", "", 1, 9, "Vigencia de demo expirada.", created),
        ]
        for v in verifs:
            conn.execute(
                """
                INSERT INTO verifications (
                    user_id, scope, status, doc_type_simulated, doc_ref_simulated, license_simulated,
                    experience_note, consent_accepted, reviewed_by, review_reason, reviewed_at, is_simulated, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (*v[:10], created if v[8] else None, v[10]),
            )

        # Conductoras y vehículos ficticios
        conn.execute(
            "INSERT INTO drivers (user_id, license_number_simulated, approval_status, is_available, rating_avg, trips_completed, created_at) VALUES (2, 'LIC-SIM-881', 'aprobada', 1, 4.9, 18, ?)",
            (created,),
        )
        conn.execute(
            "INSERT INTO drivers (user_id, license_number_simulated, approval_status, is_available, rating_avg, trips_completed, created_at) VALUES (3, 'LIC-SIM-992', 'aprobada', 1, 4.8, 12, ?)",
            (created,),
        )
        conn.execute(
            "INSERT INTO vehicles (driver_id, brand_model, color, plate_simulated, year, approval_status, created_at) VALUES (1, 'Suzuki Swift', 'Blanco Perla', 'DEMO-11', 2022, 'aprobada', ?)",
            (created,),
        )
        conn.execute(
            "INSERT INTO vehicles (driver_id, brand_model, color, plate_simulated, year, approval_status, created_at) VALUES (2, 'Hyundai Grand i10', 'Gris Plata', 'DEMO-22', 2021, 'aprobada', ?)",
            (created,),
        )

        # Contactos de confianza ficticios
        conn.execute(
            "INSERT INTO trusted_contacts (user_id, name, relation, phone_simulated, created_at) VALUES (1, 'Marta Riquelme (Ficticio)', 'Madre', '+56 9 0000 3001', ?)",
            (created,),
        )

        # Solicitudes de viaje (1 en negociación, 1 programada para menor acompañada [flujo propuesto], 1 completada)
        conn.execute(
            """
            INSERT INTO trip_requests (
                passenger_id, origin_comuna, origin_address_simulated, destination_comuna, destination_address_simulated,
                trip_type, scheduled_at, proposed_fare, payment_method, estimated_km, estimated_min,
                for_minor_demo, minor_label_simulated, status, expires_at, created_at
            ) VALUES (
                1, 'Chillán', 'Plaza de Armas (Simulado)', 'Chillán Viejo', 'Parque Monumental (Simulado)',
                'inmediato', NULL, 3200, 'efectivo', 4.5, 12, 0, '', 'en negociación', ?, ?
            )
            """,
            (_dt_offset(hours=2), created),
        )
        # Propuesta y contraoferta en la solicitud 1
        conn.execute(
            """
            INSERT INTO fare_proposals (trip_request_id, driver_id, proposer_role, amount, payment_method, note, status, expires_at, created_at)
            VALUES (1, 1, 'conductora', 3800, 'efectivo', 'Tráfico en Av. O’Higgins; propongo $3.800 (simulado).', 'vigente', ?, ?)
            """,
            (_dt_offset(hours=1), created),
        )

        # Solicitud 2: viaje programado propuesto para menor acompañada por adulta responsable
        conn.execute(
            """
            INSERT INTO trip_requests (
                passenger_id, origin_comuna, origin_address_simulated, destination_comuna, destination_address_simulated,
                trip_type, scheduled_at, proposed_fare, payment_method, estimated_km, estimated_min,
                for_minor_demo, minor_label_simulated, status, expires_at, created_at
            ) VALUES (
                1, 'Bulnes', 'Sector Centro Bulnes (Simulado)', 'Chillán', 'Liceo Bicentenario (Simulado)',
                'programado', ?, 9500, 'transferencia', 24.2, 32,
                1, 'Pasajera menor (15 años, perfil ficticio) — acompañada / autorizada por adulta responsable', 'solicitado', ?, ?
            )
            """,
            (_dt_offset(days=1, hours=2), _dt_offset(days=1), created),
        )

        # Solicitud 3 y Viaje completado para historial y reseña verificada
        conn.execute(
            """
            INSERT INTO trip_requests (
                passenger_id, origin_comuna, origin_address_simulated, destination_comuna, destination_address_simulated,
                trip_type, scheduled_at, proposed_fare, payment_method, estimated_km, estimated_min,
                for_minor_demo, minor_label_simulated, status, expires_at, created_at
            ) VALUES (
                1, 'Chillán', 'Terminal María Teresa (Simulado)', 'Bulnes', 'Plaza de Bulnes (Simulado)',
                'inmediato', NULL, 8500, 'pago_bera', 22.8, 29, 0, '', 'cerrado', ?, ?
            )
            """,
            (_dt_offset(days=-1), _dt_offset(days=-2)),
        )
        conn.execute(
            """
            INSERT INTO trips (
                trip_request_id, passenger_id, driver_id, vehicle_id, final_fare, payment_method,
                payment_status, trip_type, scheduled_at, status, start_pin, passenger_confirmed, driver_confirmed,
                simulated_progress, created_at, updated_at
            ) VALUES (3, 1, 1, 1, 8500, 'pago_bera', 'confirmado_simulado', 'inmediato', NULL, 'completado', '4829', 1, 1, 100, ?, ?)
            """,
            (_dt_offset(days=-2), _dt_offset(days=-2)),
        )

        # Ofertas laborales (4 aprobadas con variedad de filtros + 1 pendiente de moderación)
        jobs = [
            (6, 1, "Asistente de Control de Calidad (Part-Time)", "Agroindustria", "Chillán", "presencial", "part-time", 1, 0, 420000, "$420.000 líquido mensual (referencial)", "plazo fijo",
             "Apoyo en revisión de etiquetado y registro de lotes en planta de frutos secos.", "Revisar etiquetas, registrar planillas digitales, apoyar despacho.", "Enseñanza media completa. No requiere experiencia previa.", _dt_offset(days=15)[:10], "Postulación en BERA", "aprobada", ""),
            (6, 1, "Coordinadora de Ventas Digitales", "Comercio y Ventas", "Chillán", "remota", "full-time", 1, 1, 680000, "$680.000 líquido", "indefinido",
             "Gestión de pedidos mayoristas y atención a clientas de la Región de Ñuble en modalidad teletrabajo.", "Responder cotizaciones, coordinar envíos regionales, reportes semanales.", "1 año en ventas o administración. Manejo de planillas.", _dt_offset(days=20)[:10], "Postulación en BERA", "aprobada", ""),
            (5, None, "Apoyo en Empaque y Ferias (Fines de Semana)", "Artesanía y Cosmética", "Quillón", "presencial", "part-time", 1, 0, None, "No informada", "honorarios",
             "Apoyo en preparación de pedidos y atención de stand en ferias locales de Quillón.", "Armar cajitas, atender público, control de stock básico.", "Sin experiencia requerida. Ganas de aprender.", _dt_offset(days=10)[:10], "Postulación en BERA", "aprobada", ""),
            (6, 1, "Administrativa de Bodega y Despacho", "Logística", "San Carlos", "híbrida", "por turnos", 0, 1, 560000, "$560.000 líquido", "indefinido",
             "Control documental de guías y coordinación de rutas en Provincia de Punilla.", "Emitir guías, cuadrar inventario, coordinar retiros.", "Técnico nivel medio o superior en administración/logística.", _dt_offset(days=12)[:10], "Postulación en BERA", "aprobada", ""),
            (6, 1, "Práctica Profesional Administración", "Agroindustria", "Bulnes", "presencial", "part-time", 1, 0, 200000, "$200.000 bono locomoción/colación", "práctica",
             "Práctica para estudiante de Administración de Empresas en apoyo administrativo.", "Archivo digital, apoyo en remuneraciones y compras.", "Estudiante regular en Ñuble. Sin experiencia previa.", _dt_offset(days=25)[:10], "Postulación en BERA", "pendiente", ""),
        ]
        for j in jobs:
            conn.execute(
                """
                INSERT INTO job_offers (
                    employer_user_id, company_id, title, rubro, comuna, modality, schedule_type,
                    flexible_hours, experience_required, salary_clp, salary_note, contract_type,
                    description, tasks, requirements, closing_date, application_method,
                    moderation_status, moderation_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (*j, created),
            )

        # Postulación inicial de prueba
        conn.execute(
            """
            INSERT INTO job_applications (job_id, applicant_user_id, cover_note, cv_snapshot, status, created_at, updated_at)
            VALUES (1, 4, 'Me interesa el horario part-time para compatibilizar con mis estudios en Bulnes.', 'Daniela Paredes — Contabilidad General, Office, disponibilidad inmediata.', 'en revisión', ?, ?)
            """,
            (created, created),
        )

        # Emprendimientos
        conn.execute(
            """
            INSERT INTO ventures (
                owner_user_id, name, category, comuna, description, schedule_text, availability,
                social_handle, whatsapp_authorized, whatsapp_simulated, image_theme, moderation_status, created_at, updated_at
            ) VALUES (
                5, 'Botánica Valle del Sol (Ficticio)', 'Cosmética y Bienestar', 'Quillón',
                'Elaboración artesanal de bálsamos, jabones de rosa mosqueta y aceites esenciales con insumos de Ñuble.',
                'Lunes a sábado, 10:00 a 19:00 hrs', 'Disponible con entregas en Quillón y Chillán',
                '@botanica.quillon.demo', 1, '+56 9 0000 5555 (Ficticio)', 'botanica', 'aprobada', ?, ?
            )
            """,
            (created, created),
        )
        conn.execute(
            """
            INSERT INTO ventures (
                owner_user_id, name, category, comuna, description, schedule_text, availability,
                social_handle, whatsapp_authorized, whatsapp_simulated, image_theme, moderation_status, created_at, updated_at
            ) VALUES (
                2, 'Costuras y Arreglos El Roble (Ficticio)', 'Servicios y Oficios', 'Chillán',
                'Ajustes de vestuario, bastas, cierres y confección escolar a medida en sector centro.',
                'Martes a viernes, 09:30 a 18:00 hrs', 'Agenda abierta esta semana',
                '@costuras.roble.demo', 0, '', 'costura', 'aprobada', ?, ?
            )
            """,
            (created, created),
        )
        conn.execute(
            """
            INSERT INTO ventures (
                owner_user_id, name, category, comuna, description, schedule_text, availability,
                social_handle, whatsapp_authorized, whatsapp_simulated, image_theme, moderation_status, created_at, updated_at
            ) VALUES (
                7, 'Dulces de Coihueco (Ficticio)', 'Alimentación y Repostería', 'Coihueco',
                'Tortas caseras y kuchen de frutos rojos por encargo.',
                'Viernes a domingo', 'En revisión',
                '@dulces.coihueco.demo', 0, '', 'reposteria', 'pendiente', ?, ?
            )
            """,
            (created, created),
        )

        # Productos/servicios de emprendimientos
        conn.executemany(
            "INSERT INTO venture_items (venture_id, title, item_type, price_clp, description) VALUES (?, ?, ?, ?, ?)",
            [
                (1, "Jabón de Rosa Mosqueta y Avena", "producto", 4500, "Barra 100g hidratante elaborada en Quillón."),
                (1, "Pack Regalo Bienestar Ñuble", "producto", 14900, "Incluye jabón, bálsamo labial y crema de manos."),
                (1, "Asesoría rutina facial natural", "servicio", None, "Consultar disponibilidad de horario."),
                (2, "Ajuste de basta pantalón", "servicio", 4000, "Entrega en 24 horas hábiles."),
                (2, "Confección a medida", "servicio", None, "Consultar valores según tela y diseño."),
                (3, "Kuchen de frambuesa 8 porciones", "producto", 12000, "Pedido con 48 horas de anticipación."),
            ],
        )

        # Favoritos
        conn.execute(
            "INSERT INTO favorites (user_id, target_type, target_id, created_at) VALUES (1, 'venture', 1, ?)",
            (created,),
        )

        # Conversación y mensajes ficticios
        conn.execute(
            "INSERT INTO conversations (context_type, context_id, participant_a_id, participant_b_id, created_at) VALUES ('trip', 1, 1, 2, ?)",
            (created,),
        )
        conn.execute(
            "INSERT INTO messages (conversation_id, sender_id, body, is_simulated_auto, created_at) VALUES (1, 2, 'Hola Camila, voy saliendo desde Av. Collín. ¿Te parece $3.800? (Mensaje demo)', 0, ?)",
            (created,),
        )

        # Reseña vinculada a viaje completado (trip_id=1)
        conn.execute(
            "INSERT INTO reviews (reviewer_id, target_user_id, context_type, context_id, rating, comment, interaction_verified, created_at) VALUES (1, 2, 'trip', 1, 5, 'Excelente coordinación, viaje puntual y vehículo muy limpio.', 1, ?)",
            (created,),
        )

        # Denuncia de ejemplo
        conn.execute(
            """
            INSERT INTO reports (reporter_id, target_type, target_id, category, description, status, created_at)
            VALUES (4, 'job', 3, 'contenido_enganoso', 'Ejemplo de reporte de demostración para probar revisión administrativa.', 'abierta', ?)
            """,
            (created,),
        )

        # Publicidad ficticia (identificada como Publicidad/Patrocinado)
        conn.executemany(
            "INSERT INTO ads (advertiser, title, body, placement, link_url, image_badge, valid_until, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("Librería Regional Ñuble (Ficticia)", "Útiles y papelería para tu emprendimiento", "15% dcto. en insumos de embalaje en Chillán.", "inicio", "#emprendimientos", "Publicidad", _dt_offset(days=30)[:10], "aprobada", created),
                ("Centro de Capacitación Digital (Ficticio)", "Talleres gratuitos de finanzas básicas", "Inscripciones abiertas para mujeres de las 21 comunas.", "empleos", "#empleos", "Patrocinado", _dt_offset(days=20)[:10], "aprobada", created),
                ("Feria Emprende Itata (Ficticia)", "Reserva tu stand en Quirihue", "Convocatoria abierta para artesanas de Itata.", "emprendimientos", "#emprendimientos", "Publicidad", _dt_offset(days=15)[:10], "pendiente", created),
            ],
        )

        # Notificaciones internas simuladas
        conn.executemany(
            "INSERT INTO notifications (user_id, title, body, category, is_read, is_simulated, created_at) VALUES (?, ?, ?, ?, 0, 1, ?)",
            [
                (1, "Nueva contraoferta de viaje (Simulada)", "Valentina propuso $3.800 para tu viaje Chillán -> Chillán Viejo.", "movilidad", created),
                (4, "Postulación en revisión (Simulada)", "AgroFrut Ñuble SpA cambió tu postulación a 'en revisión'.", "empleos", created),
                (7, "Verificación rechazada (Simulada)", "Tu documento simulado requiere corrección. Puedes apelar o reenviar desde Perfil.", "verificacion", created),
            ],
        )

        # Auditoría inicial
        conn.execute(
            "INSERT INTO audit_logs (admin_user_id, action, target_type, target_id, reason, details_json, created_at) VALUES (9, 'aprobar_verificacion', 'verification', 1, 'Documentación ficticia validada para demostración inicial.', '{\"status\":\"aprobada\"}', ?)",
            (created,),
        )

        # Parámetros configurables
        conn.executemany(
            "INSERT INTO app_config (key, value, updated_at) VALUES (?, ?, ?)",
            [
                ("commission_percent", "0 (Pendiente de definición comercial)", created),
                ("proposal_ttl_minutes", "60", created),
                ("minor_autonomous_enabled", "false", created),
                ("share_link_ttl_minutes", "120", created),
            ],
        )
