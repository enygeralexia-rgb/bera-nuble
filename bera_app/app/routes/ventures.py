"""
Módulo de Emprendimiento de BERA:
- Vitrina de emprendimientos liderados por mujeres de Ñuble (sin carrito ni pagos)
- Búsqueda y filtros, favoritos, chat y acceso a WhatsApp solo cuando está autorizado (ficticio)
- Creación y edición (cambios sensibles vuelven a estado 'en revisión')
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..config import COMUNA_NAMES
from ..database import db_session
from ..security import get_optional_user, has_approved_verification, now_iso, require_adult, require_user

router = APIRouter(prefix="/api/ventures", tags=["ventures"])


class VentureItemIn(BaseModel):
    title: str = Field(..., min_length=2, max_length=100)
    item_type: str = "producto"  # producto | servicio
    price_clp: int | None = None
    description: str = Field(..., min_length=3, max_length=300)


class VentureIn(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    category: str = Field(..., min_length=2, max_length=60)
    comuna: str
    description: str = Field(..., min_length=10, max_length=1000)
    schedule_text: str = Field(..., min_length=3, max_length=120)
    availability: str = "Disponible"
    social_handle: str = ""
    whatsapp_authorized: bool = False
    whatsapp_simulated: str = ""
    image_theme: str = "floral"
    items: list[VentureItemIn] = []


@router.get("")
def list_ventures(
    comuna: str | None = None,
    category: str | None = None,
    q: str | None = None,
    user: dict | None = Depends(get_optional_user),
):
    clauses = ["v.moderation_status = 'aprobada'"]
    params = []
    if comuna:
        clauses.append("v.comuna = ?")
        params.append(comuna)
    if category:
        clauses.append("v.category = ?")
        params.append(category)
    if q:
        clauses.append("(v.name LIKE ? OR v.description LIKE ? OR v.category LIKE ?)")
        like = f"%{q.strip()}%"
        params.extend([like, like, like])

    sql = f"""
        SELECT v.*, u.full_name AS owner_name
        FROM ventures v
        JOIN users u ON u.id = v.owner_user_id
        WHERE {' AND '.join(clauses)}
        ORDER BY v.id DESC
    """
    with db_session() as conn:
        ventures = [dict(r) for r in conn.execute(sql, params).fetchall()]
        fav_ids = set()
        my_ventures = []
        if user:
            fav_rows = conn.execute(
                "SELECT target_id FROM favorites WHERE user_id = ? AND target_type = 'venture'",
                (user["id"],),
            ).fetchall()
            fav_ids = {f["target_id"] for f in fav_rows}
            my_ventures = [
                dict(mv)
                for mv in conn.execute("SELECT * FROM ventures WHERE owner_user_id = ? ORDER BY id DESC", (user["id"],)).fetchall()
            ]

        for v in ventures:
            v["is_favorite"] = v["id"] in fav_ids
            if not v["whatsapp_authorized"]:
                v["whatsapp_simulated"] = ""
            items = conn.execute("SELECT * FROM venture_items WHERE venture_id = ?", (v["id"],)).fetchall()
            v["items"] = [dict(i) for i in items]
            rev = conn.execute(
                "SELECT ROUND(AVG(rating), 1) AS avg_rating, COUNT(*) AS cnt FROM reviews WHERE context_type = 'venture' AND context_id = ?",
                (v["id"],),
            ).fetchone()
            v["avg_rating"] = rev["avg_rating"]
            v["review_count"] = rev["cnt"]

        for mv in my_ventures:
            mv["items"] = [dict(i) for i in conn.execute("SELECT * FROM venture_items WHERE venture_id = ?", (mv["id"],)).fetchall()]

    return {"ventures": ventures, "my_ventures": my_ventures}


@router.post("")
def create_venture(payload: VentureIn, user: dict = Depends(require_adult)):
    if payload.comuna not in COMUNA_NAMES:
        raise HTTPException(status_code=400, detail="Comuna fuera de la Región de Ñuble.")
    created = now_iso()
    with db_session() as conn:
        if not has_approved_verification(conn, user["id"], "emprendedora"):
            raise HTTPException(
                status_code=403,
                detail="Debes contar con verificación aprobada de emprendedora para publicar en la vitrina.",
            )
        cur = conn.execute(
            """
            INSERT INTO ventures (
                owner_user_id, name, category, comuna, description, schedule_text, availability,
                social_handle, whatsapp_authorized, whatsapp_simulated, image_theme,
                moderation_status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pendiente', ?, ?)
            """,
            (
                user["id"],
                payload.name.strip(),
                payload.category.strip(),
                payload.comuna,
                payload.description.strip(),
                payload.schedule_text.strip(),
                payload.availability.strip(),
                payload.social_handle.strip(),
                1 if payload.whatsapp_authorized else 0,
                payload.whatsapp_simulated.strip() if payload.whatsapp_authorized else "",
                payload.image_theme,
                created,
                created,
            ),
        )
        vid = cur.lastrowid
        for it in payload.items:
            conn.execute(
                "INSERT INTO venture_items (venture_id, title, item_type, price_clp, description) VALUES (?, ?, ?, ?, ?)",
                (vid, it.title.strip(), it.item_type, it.price_clp, it.description.strip()),
            )
    return {
        "id": vid,
        "moderation_status": "pendiente",
        "message": "Emprendimiento enviado a aprobación administrativa.",
    }


@router.put("/{venture_id}")
def update_venture(venture_id: int, payload: VentureIn, user: dict = Depends(require_adult)):
    if payload.comuna not in COMUNA_NAMES:
        raise HTTPException(status_code=400, detail="Comuna fuera de la Región de Ñuble.")
    with db_session() as conn:
        existing = conn.execute("SELECT * FROM ventures WHERE id = ?", (venture_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Emprendimiento no encontrado.")
        if existing["owner_user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Solo la creadora puede editar su emprendimiento.")

        sensitive_changed = (
            existing["name"] != payload.name.strip()
            or existing["description"] != payload.description.strip()
            or existing["category"] != payload.category.strip()
            or existing["comuna"] != payload.comuna
        )
        new_status = "en revisión" if sensitive_changed else existing["moderation_status"]

        conn.execute(
            """
            UPDATE ventures
            SET name = ?, category = ?, comuna = ?, description = ?, schedule_text = ?,
                availability = ?, social_handle = ?, whatsapp_authorized = ?, whatsapp_simulated = ?,
                image_theme = ?, moderation_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                payload.name.strip(),
                payload.category.strip(),
                payload.comuna,
                payload.description.strip(),
                payload.schedule_text.strip(),
                payload.availability.strip(),
                payload.social_handle.strip(),
                1 if payload.whatsapp_authorized else 0,
                payload.whatsapp_simulated.strip() if payload.whatsapp_authorized else "",
                payload.image_theme,
                new_status,
                now_iso(),
                venture_id,
            ),
        )
        if payload.items:
            conn.execute("DELETE FROM venture_items WHERE venture_id = ?", (venture_id,))
            for it in payload.items:
                conn.execute(
                    "INSERT INTO venture_items (venture_id, title, item_type, price_clp, description) VALUES (?, ?, ?, ?, ?)",
                    (venture_id, it.title.strip(), it.item_type, it.price_clp, it.description.strip()),
                )
    return {
        "moderation_status": new_status,
        "message": (
            "Cambios sensibles detectados: el emprendimiento volvió a revisión administrativa."
            if sensitive_changed
            else "Emprendimiento actualizado."
        ),
    }


@router.post("/{venture_id}/favorite")
def toggle_favorite(venture_id: int, user: dict = Depends(require_user)):
    with db_session() as conn:
        fav = conn.execute(
            "SELECT id FROM favorites WHERE user_id = ? AND target_type = 'venture' AND target_id = ?",
            (user["id"], venture_id),
        ).fetchone()
        if fav:
            conn.execute("DELETE FROM favorites WHERE id = ?", (fav["id"],))
            return {"favorite": False, "message": "Eliminado de favoritos."}
        conn.execute(
            "INSERT INTO favorites (user_id, target_type, target_id, created_at) VALUES (?, 'venture', ?, ?)",
            (user["id"], venture_id, now_iso()),
        )
    return {"favorite": True, "message": "Guardado en favoritos."}


@router.post("/{venture_id}/contact")
def contact_venture(venture_id: int, message: str = "Hola, me interesa conocer más sobre tus productos/servicios.", user: dict = Depends(require_user)):
    created = now_iso()
    with db_session() as conn:
        v = conn.execute("SELECT * FROM ventures WHERE id = ? AND moderation_status = 'aprobada'", (venture_id,)).fetchone()
        if not v:
            raise HTTPException(status_code=404, detail="Emprendimiento no disponible.")
        if v["owner_user_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="No puedes enviarte un contacto comercial a ti misma.")
        blocked = conn.execute(
            "SELECT 1 FROM blocks WHERE (blocker_id = ? AND blocked_id = ?) OR (blocker_id = ? AND blocked_id = ?)",
            (user["id"], v["owner_user_id"], v["owner_user_id"], user["id"]),
        ).fetchone()
        if blocked:
            raise HTTPException(status_code=403, detail="No es posible iniciar conversación debido a un bloqueo activo.")

        conv = conn.execute(
            """
            SELECT id FROM conversations
            WHERE context_type = 'venture' AND context_id = ?
              AND ((participant_a_id = ? AND participant_b_id = ?) OR (participant_a_id = ? AND participant_b_id = ?))
            """,
            (venture_id, user["id"], v["owner_user_id"], v["owner_user_id"], user["id"]),
        ).fetchone()
        if not conv:
            c_cur = conn.execute(
                "INSERT INTO conversations (context_type, context_id, participant_a_id, participant_b_id, created_at) VALUES ('venture', ?, ?, ?, ?)",
                (venture_id, user["id"], v["owner_user_id"], created),
            )
            conv_id = c_cur.lastrowid
        else:
            conv_id = conv["id"]

        conn.execute(
            "INSERT INTO messages (conversation_id, sender_id, body, is_simulated_auto, created_at) VALUES (?, ?, ?, 0, ?)",
            (conv_id, user["id"], message.strip(), created),
        )
        conn.execute("UPDATE ventures SET contact_count = contact_count + 1 WHERE id = ?", (venture_id,))
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, 'Nuevo contacto comercial (Simulado)', ?, 'emprendimientos', 1, ?)",
            (v["owner_user_id"], f"{user['full_name']} escribió sobre {v['name']}.", created),
        )
    return {"conversation_id": conv_id, "message": "Mensaje enviado por el chat interno de BERA."}
