"""
Rutas de autenticación, registro, acceso de demostración, invitadas, apelaciones y privacidad.
"""
import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from ..config import COMUNA_NAMES, EMAIL_PROVIDER_ENABLED, GOOGLE_OAUTH_ENABLED
from ..database import db_session
from ..security import (
    create_session,
    get_optional_user,
    hash_password,
    now_iso,
    require_user,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: str = Field(..., min_length=5, max_length=120)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=100)
    comuna: str
    birth_year: int = Field(..., ge=1920, le=2025)
    intent: str  # utilizar servicios | ofrecer servicios | ambas
    account_type: str = "personal"  # personal | empresa
    company_name: str = ""
    company_rut_simulated: str = ""
    company_rubro: str = ""
    eligibility_declared: bool = True
    consent_accepted: bool = True
    phone_simulated: str = ""


class LoginIn(BaseModel):
    email: str
    password: str


class DemoLoginIn(BaseModel):
    email: str


class AppealIn(BaseModel):
    reason: str = Field(..., min_length=10, max_length=500)


class PrivacyIn(BaseModel):
    show_comuna: bool = True
    allow_chat: bool = True


class ProfileUpdateIn(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=100)
    comuna: str
    cv_summary: str = ""
    cv_skills: str = ""


class VerificationSubmitIn(BaseModel):
    scope: str  # identidad | conductora | empleadora | emprendedora | empresa
    doc_type_simulated: str
    doc_ref_simulated: str
    license_simulated: str = ""
    experience_note: str = ""
    vehicle_brand_model: str = ""
    vehicle_color: str = ""
    vehicle_plate_simulated: str = ""
    vehicle_year: int = 2020
    consent_accepted: bool = True


@router.get("/providers")
def get_auth_providers():
    return {
        "google_oauth_enabled": GOOGLE_OAUTH_ENABLED,
        "google_oauth_message": (
            "Inicio con Google disponible."
            if GOOGLE_OAUTH_ENABLED
            else "Inicio con Google no configurado en esta demostración (requiere credenciales OAuth reales)."
        ),
        "email_provider_enabled": EMAIL_PROVIDER_ENABLED,
        "email_message": (
            "Proveedor de correo configurado."
            if EMAIL_PROVIDER_ENABLED
            else "Verificación de correo y recuperación de contraseña simuladas en demostración."
        ),
    }


@router.get("/demo-accounts")
def list_demo_accounts():
    with db_session() as conn:
        rows = conn.execute(
            "SELECT id, email, full_name, comuna, roles_json, admin_level FROM users WHERE email LIKE '%@bera.cl' ORDER BY id"
        ).fetchall()
    result = []
    for r in rows:
        result.append(
            {
                "id": r["id"],
                "email": r["email"],
                "full_name": r["full_name"],
                "comuna": r["comuna"],
                "roles": json.loads(r["roles_json"]),
                "admin_level": r["admin_level"],
                "password_hint": "BeraDemo2026!",
            }
        )
    return {"accounts": result}


@router.post("/register")
def register(payload: RegisterIn, response: Response):
    if payload.comuna not in COMUNA_NAMES:
        raise HTTPException(status_code=400, detail="La comuna seleccionada no pertenece al catálogo verificado de la Región de Ñuble.")
    if payload.intent not in ("utilizar servicios", "ofrecer servicios", "ambas"):
        raise HTTPException(status_code=400, detail="Opción inválida para '¿Qué te gustaría hacer en BERA?'.")
    if not payload.eligibility_declared or not payload.consent_accepted:
        raise HTTPException(
            status_code=400,
            detail="Debes aceptar la declaración de elegibilidad (plataforma dirigida a mujeres) y las condiciones de uso.",
        )

    current_year = datetime.now().year
    age = current_year - payload.birth_year
    if age < 18:
        raise HTTPException(
            status_code=403,
            detail="Las cuentas autónomas, empleabilidad y emprendimiento requieren ser mayor de 18 años. En movilidad, las menores solo cuentan con un flujo propuesto acompañadas por una adulta responsable.",
        )

    roles = ["pasajera"]
    if payload.intent in ("utilizar servicios", "ambas"):
        roles.append("postulante")
    if payload.account_type == "empresa":
        roles = ["empresa"]

    email_norm = payload.email.strip().lower()
    created = now_iso()

    with db_session() as conn:
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email_norm,)).fetchone()
        if existing:
            raise HTTPException(status_code=409, detail="Ya existe una cuenta registrada con ese correo.")

        cur = conn.execute(
            """
            INSERT INTO users (
                email, password_hash, full_name, comuna, phone_simulated, birth_year, is_adult,
                intent, roles_json, eligibility_declared, account_status, email_verified, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, 1, ?, ?, 1, 'activa', 0, ?)
            """,
            (
                email_norm,
                hash_password(payload.password),
                payload.full_name.strip(),
                payload.comuna,
                payload.phone_simulated.strip(),
                payload.birth_year,
                payload.intent,
                json.dumps(roles),
                created,
            ),
        )
        user_id = cur.lastrowid

        conn.execute(
            "INSERT INTO consents (user_id, consent_type, version, accepted, created_at) VALUES (?, 'elegibilidad_y_terminos', 'v1-demo', 1, ?)",
            (user_id, created),
        )

        if payload.account_type == "empresa":
            if not payload.company_name.strip():
                raise HTTPException(status_code=400, detail="Ingresa el nombre de la empresa representada.")
            conn.execute(
                """
                INSERT INTO companies (representative_user_id, name, rut_simulated, rubro, comuna, authorization_status, created_at)
                VALUES (?, ?, ?, ?, ?, 'pendiente', ?)
                """,
                (
                    user_id,
                    payload.company_name.strip(),
                    payload.company_rut_simulated.strip() or "RUT-SIM-PENDIENTE",
                    payload.company_rubro.strip() or "General",
                    payload.comuna,
                    created,
                ),
            )

        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, ?, ?, 'cuenta', 1, ?)",
            (
                user_id,
                "Bienvenida a BERA (Verificación de correo simulada)",
                "Tu cuenta fue creada en modo demostración. Puedes simular la verificación de correo y enviar tu verificación de identidad desde Perfil.",
                created,
            ),
        )

    token = create_session(user_id)
    response.set_cookie("bera_session", token, httponly=True, samesite="lax")
    return {
        "token": token,
        "message": "Cuenta creada exitosamente (verificación de correo simulada en demostración).",
    }


@router.post("/login")
def login(payload: LoginIn, response: Response):
    email_norm = payload.email.strip().lower()
    with db_session() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (email_norm,)).fetchone()
        if not row or not verify_password(payload.password, row["password_hash"]):
            raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
        if row["account_status"] == "suspendida":
            raise HTTPException(status_code=403, detail="Cuenta suspendida. Puedes apelar enviando un ticket desde soporte.")
        user_id = row["id"]

    token = create_session(user_id)
    response.set_cookie("bera_session", token, httponly=True, samesite="lax")
    return {"token": token, "message": "Sesión iniciada."}


@router.post("/demo-login")
def demo_login(payload: DemoLoginIn, response: Response):
    email_norm = payload.email.strip().lower()
    with db_session() as conn:
        row = conn.execute("SELECT id, account_status FROM users WHERE email = ?", (email_norm,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Cuenta de demostración no encontrada.")
        user_id = row["id"]
    token = create_session(user_id)
    response.set_cookie("bera_session", token, httponly=True, samesite="lax")
    return {"token": token, "message": f"Sesión demo iniciada como {email_norm}."}


@router.post("/logout")
def logout(response: Response, user: dict | None = Depends(get_optional_user)):
    response.delete_cookie("bera_session")
    return {"message": "Sesión cerrada."}


@router.get("/me")
def me(user: dict | None = Depends(get_optional_user)):
    if not user:
        return {"authenticated": False, "guest": True, "user": None}
    with db_session() as conn:
        verifs = [
            dict(v)
            for v in conn.execute(
                "SELECT id, scope, status, doc_type_simulated, doc_ref_simulated, review_reason, is_simulated, created_at FROM verifications WHERE user_id = ? ORDER BY id DESC",
                (user["id"],),
            ).fetchall()
        ]
        driver = conn.execute("SELECT * FROM drivers WHERE user_id = ?", (user["id"],)).fetchone()
        vehicle = None
        if driver:
            v_row = conn.execute("SELECT * FROM vehicles WHERE driver_id = ?", (driver["id"],)).fetchone()
            vehicle = dict(v_row) if v_row else None
        company = conn.execute("SELECT * FROM companies WHERE representative_user_id = ?", (user["id"],)).fetchone()
    return {
        "authenticated": True,
        "guest": False,
        "user": user,
        "verifications": verifs,
        "driver": dict(driver) if driver else None,
        "vehicle": vehicle,
        "company": dict(company) if company else None,
    }


@router.post("/simulate-email-verify")
def simulate_email_verify(user: dict = Depends(require_user)):
    with db_session() as conn:
        conn.execute("UPDATE users SET email_verified = 1 WHERE id = ?", (user["id"],))
    return {"message": "Correo marcado como verificado (simulado en demostración)."}


@router.post("/simulate-password-reset")
def simulate_password_reset(email: str):
    return {
        "simulated": True,
        "message": f"Simulación: si '{email}' está registrado, se habría enviado un enlace de recuperación (sin envío real de correos en esta demo).",
    }


@router.post("/profile")
def update_profile(payload: ProfileUpdateIn, user: dict = Depends(require_user)):
    if payload.comuna not in COMUNA_NAMES:
        raise HTTPException(status_code=400, detail="Comuna fuera de la Región de Ñuble.")
    with db_session() as conn:
        conn.execute(
            "UPDATE users SET full_name = ?, comuna = ?, cv_summary = ?, cv_skills = ? WHERE id = ?",
            (payload.full_name.strip(), payload.comuna, payload.cv_summary.strip(), payload.cv_skills.strip(), user["id"]),
        )
    return {"message": "Perfil actualizado."}


@router.post("/privacy")
def update_privacy(payload: PrivacyIn, user: dict = Depends(require_user)):
    with db_session() as conn:
        conn.execute(
            "UPDATE users SET privacy_settings_json = ? WHERE id = ?",
            (json.dumps(payload.model_dump()), user["id"]),
        )
    return {"message": "Configuración de privacidad guardada."}


@router.post("/appeal")
def submit_appeal(payload: AppealIn, user: dict = Depends(require_user)):
    with db_session() as conn:
        conn.execute(
            "UPDATE users SET eligibility_appeal_status = 'pendiente', eligibility_appeal_reason = ? WHERE id = ?",
            (payload.reason.strip(), user["id"]),
        )
    return {"message": "Apelación registrada para revisión administrativa."}


@router.post("/request-deletion")
def request_account_deletion(user: dict = Depends(require_user)):
    with db_session() as conn:
        conn.execute("UPDATE users SET account_status = 'eliminacion_solicitada' WHERE id = ?", (user["id"],))
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, 'Solicitud de eliminación recibida', 'Tu solicitud de eliminación de cuenta fue registrada (simulación demo).', 'privacidad', 1, ?)",
            (user["id"], now_iso()),
        )
    return {"message": "Solicitud de eliminación de cuenta registrada."}


@router.post("/verifications")
def submit_verification(payload: VerificationSubmitIn, user: dict = Depends(require_user)):
    if payload.scope not in ("identidad", "conductora", "empleadora", "emprendedora", "empresa"):
        raise HTTPException(status_code=400, detail="Ámbito de verificación inválido.")
    if not payload.consent_accepted:
        raise HTTPException(status_code=400, detail="Debes aceptar el consentimiento específico para verificación.")
    if payload.scope == "conductora" and not payload.license_simulated.strip():
        raise HTTPException(status_code=400, detail="Para ofrecer transporte debes indicar licencia de conducir simulada.")

    created = now_iso()
    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO verifications (
                user_id, scope, status, doc_type_simulated, doc_ref_simulated, license_simulated,
                experience_note, consent_accepted, is_simulated, created_at
            ) VALUES (?, ?, 'en revisión', ?, ?, ?, ?, 1, 1, ?)
            """,
            (
                user["id"],
                payload.scope,
                payload.doc_type_simulated.strip(),
                payload.doc_ref_simulated.strip(),
                payload.license_simulated.strip(),
                payload.experience_note.strip(),
                created,
            ),
        )
        verif_id = cur.lastrowid

        if payload.scope == "conductora":
            drv = conn.execute("SELECT id FROM drivers WHERE user_id = ?", (user["id"],)).fetchone()
            if not drv:
                d_cur = conn.execute(
                    "INSERT INTO drivers (user_id, license_number_simulated, approval_status, created_at) VALUES (?, ?, 'en revisión', ?)",
                    (user["id"], payload.license_simulated.strip(), created),
                )
                drv_id = d_cur.lastrowid
            else:
                drv_id = drv["id"]
                conn.execute(
                    "UPDATE drivers SET license_number_simulated = ?, approval_status = 'en revisión' WHERE id = ?",
                    (payload.license_simulated.strip(), drv_id),
                )
            if payload.vehicle_brand_model.strip():
                veh = conn.execute("SELECT id FROM vehicles WHERE driver_id = ?", (drv_id,)).fetchone()
                if not veh:
                    conn.execute(
                        "INSERT INTO vehicles (driver_id, brand_model, color, plate_simulated, year, approval_status, created_at) VALUES (?, ?, ?, ?, ?, 'en revisión', ?)",
                        (
                            drv_id,
                            payload.vehicle_brand_model.strip(),
                            payload.vehicle_color.strip() or "Blanco",
                            payload.vehicle_plate_simulated.strip() or "DEMO-99",
                            payload.vehicle_year,
                            created,
                        ),
                    )
    return {
        "id": verif_id,
        "status": "en revisión",
        "message": "Verificación simulada enviada a revisión administrativa.",
    }
