"""
Panel de Administración de BERA:
- 4 cuentas individuales con permisos configurables
- Revisión de identidades simuladas, conductoras/vehículos, empleos, emprendimientos, denuncias, apelaciones y publicidad
- Trazabilidad (auditoría con responsable, fecha y motivo)
- Prevención de resoluciones contradictorias sobre una misma solicitud
- Indicadores claramente identificados como datos de demostración
"""
import json
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..database import db_session
from ..security import now_iso, require_admin_permission, require_user

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ModerationDecisionIn(BaseModel):
    status: str  # aprobada | rechazada | vencida | en revisión | resuelta | desestimada
    reason: str = Field(..., min_length=4, max_length=400)


class UserStatusIn(BaseModel):
    account_status: str  # activa | suspendida
    reason: str = Field(..., min_length=4, max_length=400)


class AdIn(BaseModel):
    advertiser: str
    title: str
    body: str
    placement: str
    link_url: str
    valid_until: str


def _require_any_admin(user: dict = Depends(require_user)) -> dict:
    if "admin" not in user.get("roles", []) and not user.get("admin_level"):
        raise HTTPException(status_code=403, detail="Acceso restringido a administración.")
    return user


def _log_audit(conn, admin_id: int, action: str, target_type: str, target_id: int, reason: str, details: dict):
    conn.execute(
        "INSERT INTO audit_logs (admin_user_id, action, target_type, target_id, reason, details_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (admin_id, action, target_type, target_id, reason, json.dumps(details), now_iso()),
    )


@router.get("/dashboard")
def admin_dashboard(admin: dict = Depends(_require_any_admin)):
    with db_session() as conn:
        indicators = {
            "is_demo_data": True,
            "notice": "Indicadores de demostración (datos ficticios). No confundir contactos comerciales con ventas ni postulaciones con contrataciones.",
            "active_users": conn.execute("SELECT COUNT(*) AS c FROM users WHERE account_status = 'activa'").fetchone()["c"],
            "pending_verifications": conn.execute("SELECT COUNT(*) AS c FROM verifications WHERE status IN ('pendiente', 'en revisión')").fetchone()["c"],
            "trips_confirmed": conn.execute("SELECT COUNT(*) AS c FROM trips WHERE status = 'confirmado'").fetchone()["c"],
            "trips_completed": conn.execute("SELECT COUNT(*) AS c FROM trips WHERE status = 'completado'").fetchone()["c"],
            "trips_canceled": conn.execute("SELECT COUNT(*) AS c FROM trips WHERE status = 'cancelado'").fetchone()["c"],
            "job_applications": conn.execute("SELECT COUNT(*) AS c FROM job_applications WHERE status != 'retirada'").fetchone()["c"],
            "active_ventures": conn.execute("SELECT COUNT(*) AS c FROM ventures WHERE moderation_status = 'aprobada'").fetchone()["c"],
            "commercial_contacts": conn.execute("SELECT COALESCE(SUM(contact_count), 0) AS c FROM ventures").fetchone()["c"],
            "open_reports": conn.execute("SELECT COUNT(*) AS c FROM reports WHERE status IN ('abierta', 'en revisión')").fetchone()["c"],
        }

        verifications = [
            dict(r)
            for r in conn.execute(
                """
                SELECT v.*, u.full_name, u.email, u.comuna, adm.full_name AS reviewer_name
                FROM verifications v
                JOIN users u ON u.id = v.user_id
                LEFT JOIN users adm ON adm.id = v.reviewed_by
                ORDER BY v.id DESC
                """
            ).fetchall()
        ]
        jobs = [
            dict(r)
            for r in conn.execute(
                "SELECT j.*, u.full_name AS employer_name FROM job_offers j JOIN users u ON u.id = j.employer_user_id ORDER BY j.id DESC"
            ).fetchall()
        ]
        ventures = [
            dict(r)
            for r in conn.execute(
                "SELECT v.*, u.full_name AS owner_name FROM ventures v JOIN users u ON u.id = v.owner_user_id ORDER BY v.id DESC"
            ).fetchall()
        ]
        reports = [
            dict(r)
            for r in conn.execute(
                "SELECT rp.*, u.full_name AS reporter_name FROM reports rp JOIN users u ON u.id = rp.reporter_id ORDER BY rp.id DESC"
            ).fetchall()
        ]
        appeals = [
            dict(r)
            for r in conn.execute(
                "SELECT id, full_name, email, comuna, eligibility_appeal_status, eligibility_appeal_reason, account_status FROM users WHERE eligibility_appeal_status != 'ninguna' OR account_status = 'suspendida'"
            ).fetchall()
        ]
        ads = [dict(r) for r in conn.execute("SELECT * FROM ads ORDER BY id DESC").fetchall()]
        audit_logs = [
            dict(r)
            for r in conn.execute(
                "SELECT a.*, u.full_name AS admin_name, u.admin_level FROM audit_logs a JOIN users u ON u.id = a.admin_user_id ORDER BY a.id DESC LIMIT 40"
            ).fetchall()
        ]
        config_rows = [dict(r) for r in conn.execute("SELECT * FROM app_config").fetchall()]

    return {
        "admin": {
            "id": admin["id"],
            "full_name": admin["full_name"],
            "admin_level": admin["admin_level"],
            "permissions": admin["admin_permissions"],
        },
        "indicators": indicators,
        "verifications": verifications,
        "jobs": jobs,
        "ventures": ventures,
        "reports": reports,
        "appeals": appeals,
        "ads": ads,
        "audit_logs": audit_logs,
        "config": config_rows,
    }


@router.post("/verifications/{verif_id}/decide")
def decide_verification(
    verif_id: int,
    payload: ModerationDecisionIn,
    admin: dict = Depends(require_admin_permission("verifications")),
):
    if payload.status not in ("aprobada", "rechazada", "vencida", "en revisión"):
        raise HTTPException(status_code=400, detail="Estado de verificación inválido.")

    with db_session() as conn:
        v = conn.execute("SELECT * FROM verifications WHERE id = ?", (verif_id,)).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Verificación no encontrada.")
        # Prevenir resoluciones contradictorias si otra admin ya resolvió definitivamente
        if v["status"] in ("aprobada", "rechazada") and v["reviewed_by"] and v["reviewed_by"] != admin["id"] and payload.status != v["status"]:
            raise HTTPException(
                status_code=409,
                detail=f"Resolución bloqueada: esta solicitud ya fue marcada como '{v['status']}' por otra administradora. Revisa el registro de auditoría.",
            )

        conn.execute(
            "UPDATE verifications SET status = ?, reviewed_by = ?, review_reason = ?, reviewed_at = ? WHERE id = ?",
            (payload.status, admin["id"], payload.reason.strip(), now_iso(), verif_id),
        )
        if v["scope"] == "conductora":
            conn.execute("UPDATE drivers SET approval_status = ? WHERE user_id = ?", (payload.status, v["user_id"]))
            drv = conn.execute("SELECT id FROM drivers WHERE user_id = ?", (v["user_id"],)).fetchone()
            if drv:
                conn.execute("UPDATE vehicles SET approval_status = ? WHERE driver_id = ?", (payload.status, drv["id"]))
        if v["scope"] == "empresa":
            conn.execute("UPDATE companies SET authorization_status = ? WHERE representative_user_id = ?", (payload.status, v["user_id"]))

        _log_audit(conn, admin["id"], f"verificacion_{payload.status}", "verification", verif_id, payload.reason.strip(), {"scope": v["scope"]})
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, 'Actualización de verificación (Simulada)', ?, 'verificacion', 1, ?)",
            (v["user_id"], f"Tu verificación ({v['scope']}) pasó a estado '{payload.status}'. Motivo: {payload.reason.strip()}", now_iso()),
        )
    return {"message": f"Verificación #{verif_id} actualizada a '{payload.status}'."}


@router.post("/jobs/{job_id}/decide")
def decide_job(job_id: int, payload: ModerationDecisionIn, admin: dict = Depends(require_admin_permission("jobs"))):
    if payload.status not in ("aprobada", "rechazada"):
        raise HTTPException(status_code=400, detail="Estado inválido.")
    with db_session() as conn:
        job = conn.execute("SELECT * FROM job_offers WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Oferta no encontrada.")
        conn.execute(
            "UPDATE job_offers SET moderation_status = ?, moderation_reason = ? WHERE id = ?",
            (payload.status, payload.reason.strip(), job_id),
        )
        _log_audit(conn, admin["id"], f"empleo_{payload.status}", "job_offer", job_id, payload.reason.strip(), {})
    return {"message": f"Oferta laboral #{job_id} marcada como '{payload.status}'."}


@router.post("/ventures/{venture_id}/decide")
def decide_venture(venture_id: int, payload: ModerationDecisionIn, admin: dict = Depends(require_admin_permission("ventures"))):
    if payload.status not in ("aprobada", "rechazada"):
        raise HTTPException(status_code=400, detail="Estado inválido.")
    with db_session() as conn:
        v = conn.execute("SELECT * FROM ventures WHERE id = ?", (venture_id,)).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Emprendimiento no encontrado.")
        conn.execute(
            "UPDATE ventures SET moderation_status = ?, moderation_reason = ? WHERE id = ?",
            (payload.status, payload.reason.strip(), venture_id),
        )
        _log_audit(conn, admin["id"], f"emprendimiento_{payload.status}", "venture", venture_id, payload.reason.strip(), {})
    return {"message": f"Emprendimiento #{venture_id} marcado como '{payload.status}'."}


@router.post("/reports/{report_id}/decide")
def decide_report(report_id: int, payload: ModerationDecisionIn, admin: dict = Depends(require_admin_permission("reports"))):
    if payload.status not in ("resuelta", "desestimada", "en revisión"):
        raise HTTPException(status_code=400, detail="Estado de denuncia inválido.")
    with db_session() as conn:
        rp = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
        if not rp:
            raise HTTPException(status_code=404, detail="Denuncia no encontrada.")
        conn.execute(
            "UPDATE reports SET status = ?, resolved_by = ?, resolution_note = ?, resolved_at = ? WHERE id = ?",
            (payload.status, admin["id"], payload.reason.strip(), now_iso(), report_id),
        )
        _log_audit(conn, admin["id"], f"denuncia_{payload.status}", "report", report_id, payload.reason.strip(), {})
    return {"message": f"Denuncia #{report_id} actualizada a '{payload.status}'."}


@router.post("/users/{user_id}/status")
def set_user_status(user_id: int, payload: UserStatusIn, admin: dict = Depends(require_admin_permission("appeals"))):
    if payload.account_status not in ("activa", "suspendida"):
        raise HTTPException(status_code=400, detail="Estado de cuenta inválido.")
    with db_session() as conn:
        u = conn.execute("SELECT id, admin_level FROM users WHERE id = ?", (user_id,)).fetchone()
        if not u:
            raise HTTPException(status_code=404, detail="Usuaria no encontrada.")
        if u["admin_level"]:
            raise HTTPException(status_code=403, detail="No puedes suspender una cuenta de administración desde este flujo.")
        conn.execute("UPDATE users SET account_status = ? WHERE id = ?", (payload.account_status, user_id))
        _log_audit(conn, admin["id"], f"cuenta_{payload.account_status}", "user", user_id, payload.reason.strip(), {})
    return {"message": f"Cuenta #{user_id} actualizada a '{payload.account_status}'."}


@router.post("/ads")
def create_ad(payload: AdIn, admin: dict = Depends(require_admin_permission("ads"))):
    with db_session() as conn:
        cur = conn.execute(
            "INSERT INTO ads (advertiser, title, body, placement, link_url, image_badge, valid_until, status, created_at) VALUES (?, ?, ?, ?, ?, 'Publicidad', ?, 'aprobada', ?)",
            (payload.advertiser, payload.title, payload.body, payload.placement, payload.link_url, payload.valid_until, now_iso()),
        )
        _log_audit(conn, admin["id"], "crear_anuncio", "ad", cur.lastrowid, "Anuncio ficticio aprobado para demostración.", {})
    return {"id": cur.lastrowid, "message": "Anuncio ficticio publicado."}


@router.post("/ads/{ad_id}/decide")
def decide_ad(ad_id: int, payload: ModerationDecisionIn, admin: dict = Depends(require_admin_permission("ads"))):
    if payload.status not in ("aprobada", "rechazada", "pausada"):
        raise HTTPException(status_code=400, detail="Estado inválido.")
    with db_session() as conn:
        conn.execute("UPDATE ads SET status = ? WHERE id = ?", (payload.status, ad_id))
        _log_audit(conn, admin["id"], f"anuncio_{payload.status}", "ad", ad_id, payload.reason.strip(), {})
    return {"message": f"Anuncio #{ad_id} actualizado a '{payload.status}'."}
