"""
Funciones comunes de BERA:
- Chat con verificación de bloqueos y respuesta simulada opcional
- Notificaciones internas, favoritos, agenda, historial
- Reseñas vinculadas a interacciones comprobables
- Bloqueos, denuncias, publicidad identificada y centro de ayuda
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..database import db_session
from ..security import get_optional_user, now_iso, require_user

router = APIRouter(prefix="/api/common", tags=["common"])


class MessageIn(BaseModel):
    body: str = Field(..., min_length=1, max_length=1000)
    simulate_auto_reply: bool = False


class ReviewIn(BaseModel):
    context_type: str  # trip | venture
    context_id: int
    rating: int = Field(..., ge=1, le=5)
    comment: str = Field(..., min_length=4, max_length=500)


class ReportIn(BaseModel):
    target_type: str  # trip | job | venture | user
    target_id: int
    category: str
    description: str = Field(..., min_length=8, max_length=600)


class BlockIn(BaseModel):
    blocked_user_id: int
    reason: str = ""


@router.get("/home-summary")
def home_summary(user: dict | None = Depends(get_optional_user)):
    with db_session() as conn:
        featured_jobs = [
            dict(r)
            for r in conn.execute(
                "SELECT id, title, rubro, comuna, modality, schedule_type, flexible_hours, experience_required, salary_note FROM job_offers WHERE moderation_status = 'aprobada' ORDER BY id DESC LIMIT 3"
            ).fetchall()
        ]
        featured_ventures = [
            dict(r)
            for r in conn.execute(
                "SELECT id, name, category, comuna, availability, image_theme FROM ventures WHERE moderation_status = 'aprobada' ORDER BY id DESC LIMIT 3"
            ).fetchall()
        ]
        ads = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM ads WHERE status = 'aprobada' ORDER BY id DESC"
            ).fetchall()
        ]
        recent_activity = []
        unread_notifications = 0
        if user:
            recent_activity = [
                dict(n)
                for n in conn.execute(
                    "SELECT id, title, body, category, is_read, created_at FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 4",
                    (user["id"],),
                ).fetchall()
            ]
            unread_notifications = conn.execute(
                "SELECT COUNT(*) AS c FROM notifications WHERE user_id = ? AND is_read = 0",
                (user["id"],),
            ).fetchone()["c"]
    return {
        "featured_jobs": featured_jobs,
        "featured_ventures": featured_ventures,
        "ads": ads,
        "recent_activity": recent_activity,
        "unread_notifications": unread_notifications,
    }


@router.get("/conversations")
def list_conversations(user: dict = Depends(require_user)):
    with db_session() as conn:
        rows = conn.execute(
            """
            SELECT c.*, ua.full_name AS name_a, ub.full_name AS name_b
            FROM conversations c
            JOIN users ua ON ua.id = c.participant_a_id
            JOIN users ub ON ub.id = c.participant_b_id
            WHERE c.participant_a_id = ? OR c.participant_b_id = ?
            ORDER BY c.id DESC
            """,
            (user["id"], user["id"]),
        ).fetchall()
        result = []
        for r in rows:
            d = dict(r)
            other_id = d["participant_b_id"] if d["participant_a_id"] == user["id"] else d["participant_a_id"]
            d["other_user_id"] = other_id
            d["other_name"] = d["name_b"] if d["participant_a_id"] == user["id"] else d["name_a"]
            msgs = conn.execute(
                """
                SELECT m.*, u.full_name AS sender_name
                FROM messages m
                JOIN users u ON u.id = m.sender_id
                WHERE m.conversation_id = ?
                ORDER BY m.id ASC
                """,
                (d["id"],),
            ).fetchall()
            d["messages"] = [dict(m) for m in msgs]
            result.append(d)
    return {"conversations": result}


@router.post("/conversations/{conv_id}/messages")
def send_message(conv_id: int, payload: MessageIn, user: dict = Depends(require_user)):
    created = now_iso()
    with db_session() as conn:
        conv = conn.execute("SELECT * FROM conversations WHERE id = ?", (conv_id,)).fetchone()
        if not conv or user["id"] not in (conv["participant_a_id"], conv["participant_b_id"]):
            raise HTTPException(status_code=403, detail="No tienes acceso a esta conversación.")
        other_id = conv["participant_b_id"] if conv["participant_a_id"] == user["id"] else conv["participant_a_id"]
        blocked = conn.execute(
            "SELECT 1 FROM blocks WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)",
            (user["id"], other_id, other_id, user["id"]),
        ).fetchone()
        if blocked:
            raise HTTPException(status_code=403, detail="Mensajería bloqueada entre estas cuentas.")

        conn.execute(
            "INSERT INTO messages (conversation_id, sender_id, body, is_simulated_auto, created_at) VALUES (?, ?, ?, 0, ?)",
            (conv_id, user["id"], payload.body.strip(), created),
        )
        if payload.simulate_auto_reply:
            conn.execute(
                "INSERT INTO messages (conversation_id, sender_id, body, is_simulated_auto, created_at) VALUES (?, ?, ?, 1, ?)",
                (conv_id, other_id, "[Respuesta automática simulada para demostración] ¡Recibido! Gracias por escribir por BERA.", created),
            )
    return {"message": "Mensaje enviado."}


@router.get("/notifications")
def list_notifications(user: dict = Depends(require_user)):
    with db_session() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM notifications WHERE user_id = ? ORDER BY id DESC LIMIT 30",
                (user["id"],),
            ).fetchall()
        ]
        conn.execute("UPDATE notifications SET is_read = 1 WHERE user_id = ?", (user["id"],))
    return {"notifications": rows}


@router.get("/agenda")
def get_agenda(user: dict = Depends(require_user)):
    with db_session() as conn:
        scheduled_trips = [
            dict(r)
            for r in conn.execute(
                """
                SELECT tr.id, tr.origin_comuna, tr.destination_comuna, tr.scheduled_at, tr.status, tr.proposed_fare
                FROM trip_requests tr
                WHERE tr.passenger_id = ? AND tr.trip_type = 'programado'
                ORDER BY tr.scheduled_at ASC
                """,
                (user["id"],),
            ).fetchall()
        ]
        confirmed_sched = [
            dict(r)
            for r in conn.execute(
                """
                SELECT t.id, t.scheduled_at, t.status, t.final_fare, tr.origin_comuna, tr.destination_comuna
                FROM trips t
                JOIN trip_requests tr ON tr.id = t.trip_request_id
                LEFT JOIN drivers d ON d.id = t.driver_id
                WHERE (t.passenger_id = ? OR d.user_id = ?) AND t.trip_type = 'programado'
                ORDER BY t.scheduled_at ASC
                """,
                (user["id"], user["id"]),
            ).fetchall()
        ]
    return {"scheduled_requests": scheduled_trips, "confirmed_scheduled_trips": confirmed_sched}


@router.post("/reviews")
def create_review(payload: ReviewIn, user: dict = Depends(require_user)):
    with db_session() as conn:
        if payload.context_type == "trip":
            trip = conn.execute(
                "SELECT t.*, d.user_id AS driver_user_id FROM trips t JOIN drivers d ON d.id = t.driver_id WHERE t.id = ?",
                (payload.context_id,),
            ).fetchone()
            if not trip or trip["passenger_id"] != user["id"] or trip["status"] != "completado":
                raise HTTPException(
                    status_code=403,
                    detail="Solo puedes reseñar viajes completados en los que participaste como pasajera.",
                )
            target_uid = trip["driver_user_id"]
        elif payload.context_type == "venture":
            conv = conn.execute(
                "SELECT 1 FROM conversations WHERE context_type = 'venture' AND context_id = ? AND (participant_a_id = ? OR participant_b_id = ?)",
                (payload.context_id, user["id"], user["id"]),
            ).fetchone()
            if not conv:
                raise HTTPException(
                    status_code=403,
                    detail="Solo puedes reseñar emprendimientos tras una interacción comprobable en BERA (no se etiquetan compras externas no verificables).",
                )
            v = conn.execute("SELECT owner_user_id FROM ventures WHERE id = ?", (payload.context_id,)).fetchone()
            target_uid = v["owner_user_id"] if v else None
        else:
            raise HTTPException(status_code=400, detail="Tipo de reseña inválido.")

        conn.execute(
            "INSERT INTO reviews (reviewer_id, target_user_id, context_type, context_id, rating, comment, interaction_verified, created_at) VALUES (?, ?, ?, ?, ?, ?, 1, ?)",
            (user["id"], target_uid, payload.context_type, payload.context_id, payload.rating, payload.comment.strip(), now_iso()),
        )
    return {"message": "Reseña publicada con interacción comprobable en BERA."}


@router.post("/reports")
def create_report(payload: ReportIn, user: dict = Depends(require_user)):
    with db_session() as conn:
        cur = conn.execute(
            "INSERT INTO reports (reporter_id, target_type, target_id, category, description, status, created_at) VALUES (?, ?, ?, ?, ?, 'abierta', ?)",
            (user["id"], payload.target_type, payload.target_id, payload.category, payload.description.strip(), now_iso()),
        )
    return {"id": cur.lastrowid, "message": "Denuncia registrada para revisión administrativa."}


@router.post("/blocks")
def block_user(payload: BlockIn, user: dict = Depends(require_user)):
    if payload.blocked_user_id == user["id"]:
        raise HTTPException(status_code=400, detail="No puedes bloquearte a ti misma.")
    with db_session() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO blocks (blocker_id, blocked_id, reason, created_at) VALUES (?, ?, ?, ?)",
            (user["id"], payload.blocked_user_id, payload.reason.strip(), now_iso()),
        )
    return {"message": "Usuaria bloqueada. No podrá enviarte mensajes."}


@router.get("/blocks")
def list_blocks(user: dict = Depends(require_user)):
    with db_session() as conn:
        rows = [
            dict(r)
            for r in conn.execute(
                "SELECT b.*, u.full_name AS blocked_name FROM blocks b JOIN users u ON u.id = b.blocked_id WHERE b.blocker_id = ?",
                (user["id"],),
            ).fetchall()
        ]
    return {"blocks": rows}


@router.get("/help-center")
def help_center():
    return {
        "articles": [
            {"title": "¿Qué es BERA?", "body": "Plataforma piloto para mujeres de las 21 comunas de la Región de Ñuble que centraliza movilidad, empleabilidad y emprendimiento."},
            {"title": "Alcance de esta demostración", "body": "Todos los perfiles, documentos, ubicaciones, pagos y notificaciones son simulados. No coordina viajes reales ni procesa dinero."},
            {"title": "Privacidad y datos sensibles", "body": "BERA nunca publica tu ubicación precisa, teléfono privado, documentos ni currículum. El acceso a WhatsApp en emprendimientos solo se muestra si la emprendedora lo autoriza."},
            {"title": "Seguridad y botón de ayuda", "body": "El botón de ayuda abre un flujo de prueba sin llamar a emergencias ni enviar alertas externas. BERA no promete vigilancia permanente ni respuesta de autoridades."},
        ]
    }
