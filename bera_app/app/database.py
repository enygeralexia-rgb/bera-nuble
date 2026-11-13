"""
Esquema SQLite y utilidades de persistencia para BERA.
"""
import sqlite3
import json
from contextlib import contextmanager
from .config import DB_PATH


def get_connection(db_path: str = None) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path or DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


@contextmanager
def db_session(db_path: str = None):
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    comuna TEXT NOT NULL,
    phone_simulated TEXT DEFAULT '',
    birth_year INTEGER NOT NULL,
    is_adult INTEGER NOT NULL DEFAULT 1,
    intent TEXT NOT NULL DEFAULT 'utilizar servicios', -- utilizar servicios | ofrecer servicios | ambas
    roles_json TEXT NOT NULL DEFAULT '["pasajera"]', -- pasajera, conductora, postulante, emprendedora, empresa, admin
    admin_level TEXT DEFAULT NULL, -- null or admin_1..admin_4
    admin_permissions_json TEXT DEFAULT '[]',
    eligibility_declared INTEGER NOT NULL DEFAULT 1,
    eligibility_appeal_status TEXT DEFAULT 'ninguna', -- ninguna | pendiente | aprobada | rechazada
    eligibility_appeal_reason TEXT DEFAULT '',
    account_status TEXT NOT NULL DEFAULT 'activa', -- activa | suspendida | eliminacion_solicitada
    email_verified INTEGER NOT NULL DEFAULT 0,
    privacy_settings_json TEXT NOT NULL DEFAULT '{"show_comuna": true, "allow_chat": true}',
    cv_summary TEXT DEFAULT '',
    cv_skills TEXT DEFAULT '',
    avatar_color TEXT DEFAULT '#AD285F',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    representative_user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    rut_simulated TEXT NOT NULL,
    rubro TEXT NOT NULL,
    comuna TEXT NOT NULL,
    authorization_status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | aprobada | rechazada
    created_at TEXT NOT NULL,
    FOREIGN KEY(representative_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS verifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    scope TEXT NOT NULL, -- identidad | conductora | empleadora | emprendedora | empresa
    status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | en revisión | aprobada | rechazada | vencida
    doc_type_simulated TEXT NOT NULL,
    doc_ref_simulated TEXT NOT NULL,
    license_simulated TEXT DEFAULT '',
    experience_note TEXT DEFAULT '',
    consent_accepted INTEGER NOT NULL DEFAULT 1,
    reviewed_by INTEGER DEFAULT NULL,
    review_reason TEXT DEFAULT '',
    reviewed_at TEXT DEFAULT NULL,
    is_simulated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS consents (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    consent_type TEXT NOT NULL,
    version TEXT NOT NULL DEFAULT 'v1-demo',
    accepted INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drivers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    license_number_simulated TEXT NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | en revisión | aprobada | rechazada | vencida
    is_available INTEGER NOT NULL DEFAULT 1,
    rating_avg REAL NOT NULL DEFAULT 5.0,
    trips_completed INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS vehicles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    driver_id INTEGER NOT NULL,
    brand_model TEXT NOT NULL,
    color TEXT NOT NULL,
    plate_simulated TEXT NOT NULL,
    year INTEGER NOT NULL,
    approval_status TEXT NOT NULL DEFAULT 'pendiente',
    created_at TEXT NOT NULL,
    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trusted_contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    relation TEXT NOT NULL,
    phone_simulated TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trip_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    passenger_id INTEGER NOT NULL,
    origin_comuna TEXT NOT NULL,
    origin_address_simulated TEXT NOT NULL,
    destination_comuna TEXT NOT NULL,
    destination_address_simulated TEXT NOT NULL,
    trip_type TEXT NOT NULL DEFAULT 'inmediato', -- inmediato | programado
    scheduled_at TEXT DEFAULT NULL,
    proposed_fare INTEGER NOT NULL,
    payment_method TEXT NOT NULL DEFAULT 'efectivo', -- efectivo | transferencia | pago_bera
    estimated_km REAL NOT NULL,
    estimated_min INTEGER NOT NULL,
    for_minor_demo INTEGER NOT NULL DEFAULT 0, -- flujo propuesto adulta responsable -> menor
    minor_label_simulated TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'solicitado', -- solicitado | en negociación | confirmado | cerrado | cancelado
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(passenger_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fare_proposals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_request_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    proposer_role TEXT NOT NULL, -- pasajera | conductora
    amount INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    note TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'vigente', -- vigente | aceptada | rechazada | vencida | superada
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(trip_request_id) REFERENCES trip_requests(id) ON DELETE CASCADE,
    FOREIGN KEY(driver_id) REFERENCES drivers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trip_request_id INTEGER UNIQUE NOT NULL,
    passenger_id INTEGER NOT NULL,
    driver_id INTEGER NOT NULL,
    vehicle_id INTEGER NOT NULL,
    final_fare INTEGER NOT NULL,
    payment_method TEXT NOT NULL,
    payment_status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | declarado_pasajera | confirmado_simulado
    trip_type TEXT NOT NULL,
    scheduled_at TEXT DEFAULT NULL,
    status TEXT NOT NULL DEFAULT 'confirmado', -- confirmado | conductora en camino | conductora en origen | en curso | completado | cancelado
    start_pin TEXT NOT NULL,
    passenger_confirmed INTEGER NOT NULL DEFAULT 1,
    driver_confirmed INTEGER NOT NULL DEFAULT 1,
    share_token TEXT DEFAULT NULL,
    share_expires_at TEXT DEFAULT NULL,
    share_revoked INTEGER NOT NULL DEFAULT 0,
    simulated_progress INTEGER NOT NULL DEFAULT 0, -- 0..100
    cancellation_reason TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(trip_request_id) REFERENCES trip_requests(id) ON DELETE CASCADE,
    FOREIGN KEY(passenger_id) REFERENCES users(id),
    FOREIGN KEY(driver_id) REFERENCES drivers(id),
    FOREIGN KEY(vehicle_id) REFERENCES vehicles(id)
);

CREATE TABLE IF NOT EXISTS job_offers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employer_user_id INTEGER NOT NULL,
    company_id INTEGER DEFAULT NULL,
    title TEXT NOT NULL,
    rubro TEXT NOT NULL,
    comuna TEXT NOT NULL,
    modality TEXT NOT NULL, -- presencial | remota | híbrida
    schedule_type TEXT NOT NULL, -- full-time | part-time | por turnos
    flexible_hours INTEGER NOT NULL DEFAULT 0,
    experience_required INTEGER NOT NULL DEFAULT 0,
    salary_clp INTEGER DEFAULT NULL,
    salary_note TEXT DEFAULT 'No informada',
    contract_type TEXT NOT NULL, -- indefinido | plazo fijo | honorarios | práctica
    description TEXT NOT NULL,
    tasks TEXT NOT NULL,
    requirements TEXT NOT NULL,
    closing_date TEXT NOT NULL,
    application_method TEXT NOT NULL DEFAULT 'Postulación en BERA',
    moderation_status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | aprobada | rechazada
    moderation_reason TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    FOREIGN KEY(employer_user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(company_id) REFERENCES companies(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS job_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id INTEGER NOT NULL,
    applicant_user_id INTEGER NOT NULL,
    cover_note TEXT NOT NULL,
    cv_snapshot TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'enviada', -- enviada | en revisión | preseleccionada | seleccionada | no seleccionada | retirada
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(job_id, applicant_user_id),
    FOREIGN KEY(job_id) REFERENCES job_offers(id) ON DELETE CASCADE,
    FOREIGN KEY(applicant_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ventures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_user_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    comuna TEXT NOT NULL,
    description TEXT NOT NULL,
    schedule_text TEXT NOT NULL,
    availability TEXT NOT NULL DEFAULT 'Disponible',
    social_handle TEXT DEFAULT '',
    whatsapp_authorized INTEGER NOT NULL DEFAULT 0,
    whatsapp_simulated TEXT DEFAULT '',
    image_theme TEXT DEFAULT 'floral',
    moderation_status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | en revisión | aprobada | rechazada
    moderation_reason TEXT DEFAULT '',
    contact_count INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(owner_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS venture_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    venture_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    item_type TEXT NOT NULL DEFAULT 'producto', -- producto | servicio
    price_clp INTEGER DEFAULT NULL, -- NULL = consultar
    description TEXT NOT NULL,
    FOREIGN KEY(venture_id) REFERENCES ventures(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS favorites (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    target_type TEXT NOT NULL, -- venture | job
    target_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, target_type, target_id),
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    context_type TEXT NOT NULL, -- trip | venture | direct
    context_id INTEGER DEFAULT NULL,
    participant_a_id INTEGER NOT NULL,
    participant_b_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(participant_a_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(participant_b_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL,
    sender_id INTEGER NOT NULL,
    body TEXT NOT NULL,
    is_simulated_auto INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY(sender_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reviewer_id INTEGER NOT NULL,
    target_user_id INTEGER DEFAULT NULL,
    context_type TEXT NOT NULL, -- trip | venture
    context_id INTEGER NOT NULL,
    rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),
    comment TEXT NOT NULL,
    interaction_verified INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(reviewer_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    blocker_id INTEGER NOT NULL,
    blocked_id INTEGER NOT NULL,
    reason TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    UNIQUE(blocker_id, blocked_id),
    FOREIGN KEY(blocker_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY(blocked_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reporter_id INTEGER NOT NULL,
    target_type TEXT NOT NULL, -- trip | job | venture | user
    target_id INTEGER NOT NULL,
    category TEXT NOT NULL, -- estafa | cobro_indebido | seguridad | contenido_enganoso | otro
    description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'abierta', -- abierta | en revisión | resuelta | desestimada
    resolved_by INTEGER DEFAULT NULL,
    resolution_note TEXT DEFAULT '',
    resolved_at TEXT DEFAULT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(reporter_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    advertiser TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    placement TEXT NOT NULL, -- inicio | empleos | emprendimientos
    link_url TEXT NOT NULL,
    image_badge TEXT DEFAULT 'Patrocinado',
    valid_until TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pendiente', -- pendiente | aprobada | rechazada | pausada
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'sistema',
    is_read INTEGER NOT NULL DEFAULT 0,
    is_simulated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    admin_user_id INTEGER NOT NULL,
    action TEXT NOT NULL,
    target_type TEXT NOT NULL,
    target_id INTEGER NOT NULL,
    reason TEXT NOT NULL,
    details_json TEXT DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(admin_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS app_config (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def init_db(db_path: str = None):
    with db_session(db_path) as conn:
        conn.executescript(SCHEMA_SQL)
