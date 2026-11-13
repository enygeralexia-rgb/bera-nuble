"""
Sistema de Movilidad propio de BERA:
- Solicitudes inmediatas y programadas en las 21 comunas de Ñuble
- Negociación de tarifas con contraofertas, vigencia y cierre automático al confirmar
- Prevención de doble asignación y conflictos de horario
- Estados de viaje, código PIN de inicio, simulación de ruta y pagos
- Flujo propuesto de viaje para menor acompañada por adulta responsable (deshabilitada contratación autónoma de menores)
- Contactos de confianza, enlace compartido temporal revocable y botón de ayuda de prueba
"""
import math
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from ..config import COMUNA_MAP, COMUNA_NAMES, PAYMENT_METHODS, TRIP_STATES
from ..database import db_session
from ..security import get_optional_user, has_approved_verification, now_iso, require_adult, require_user

router = APIRouter(prefix="/api/mobility", tags=["mobility"])


def _estimate_route(origin_comuna: str, dest_comuna: str) -> tuple[float, int]:
    c1 = COMUNA_MAP[origin_comuna]
    c2 = COMUNA_MAP[dest_comuna]
    if origin_comuna == dest_comuna:
        return 3.8, 11
    r = 6371.0
    lat1, lon1, lat2, lon2 = map(math.radians, [c1["lat"], c1["lng"], c2["lat"], c2["lng"]])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    km = round(r * 2 * math.asin(math.sqrt(a)) * 1.25, 1)  # factor vial aproximado
    minutes = max(10, int(round(km * 1.35 + 4)))
    return km, minutes


class TripRequestIn(BaseModel):
    origin_comuna: str
    origin_address_simulated: str = Field(..., min_length=3, max_length=120)
    destination_comuna: str
    destination_address_simulated: str = Field(..., min_length=3, max_length=120)
    trip_type: str = "inmediato"  # inmediato | programado
    scheduled_at: str | None = None
    proposed_fare: int = Field(..., ge=1000, le=200000)
    payment_method: str = "efectivo"
    for_minor_demo: bool = False
    minor_label_simulated: str = ""
    minor_autonomous_attempt: bool = False


class ProposalIn(BaseModel):
    amount: int = Field(..., ge=1000, le=200000)
    payment_method: str = "efectivo"
    note: str = ""
    driver_id: int | None = None


class TripStatusIn(BaseModel):
    status: str
    cancellation_reason: str = ""


class PaymentActionIn(BaseModel):
    action: str  # declarar_pasajera | confirmar_simulado


class TrustedContactIn(BaseModel):
    name: str = Field(..., min_length=2, max_length=80)
    relation: str = Field(..., min_length=2, max_length=50)
    phone_simulated: str = Field(..., min_length=6, max_length=30)


@router.get("/comunas")
def list_comunas():
    return {"comunas": COMUNA_NAMES}


@router.get("/overview")
def mobility_overview(user: dict | None = Depends(get_optional_user)):
    with db_session() as conn:
        open_requests = [
            dict(r)
            for r in conn.execute(
                """
                SELECT tr.*, u.full_name AS passenger_name
                FROM trip_requests tr
                JOIN users u ON u.id = tr.passenger_id
                WHERE tr.status IN ('solicitado', 'en negociación')
                ORDER BY tr.id DESC
                """
            ).fetchall()
        ]
        for req in open_requests:
            props = conn.execute(
                """
                SELECT fp.*, u.full_name AS driver_name, d.rating_avg, v.brand_model, v.color, v.plate_simulated
                FROM fare_proposals fp
                JOIN drivers d ON d.id = fp.driver_id
                JOIN users u ON u.id = d.user_id
                LEFT JOIN vehicles v ON v.driver_id = d.id
                WHERE fp.trip_request_id = ?
                ORDER BY fp.id DESC
                """,
                (req["id"],),
            ).fetchall()
            req["proposals"] = [dict(p) for p in props]

        my_trips = []
        trusted_contacts = []
        if user:
            trips_rows = conn.execute(
                """
                SELECT t.*, tr.origin_comuna, tr.origin_address_simulated, tr.destination_comuna,
                       tr.destination_address_simulated, tr.estimated_km, tr.estimated_min, tr.for_minor_demo,
                       tr.minor_label_simulated,
                       pu.full_name AS passenger_name,
                       du.full_name AS driver_name, du.id AS driver_user_id, d.rating_avg AS driver_rating,
                       v.brand_model, v.color, v.plate_simulated
                FROM trips t
                JOIN trip_requests tr ON tr.id = t.trip_request_id
                JOIN users pu ON pu.id = t.passenger_id
                JOIN drivers d ON d.id = t.driver_id
                JOIN users du ON du.id = d.user_id
                JOIN vehicles v ON v.id = t.vehicle_id
                WHERE t.passenger_id = ? OR d.user_id = ?
                ORDER BY t.id DESC
                """,
                (user["id"], user["id"]),
            ).fetchall()
            my_trips = [dict(t) for t in trips_rows]
            trusted_contacts = [
                dict(c)
                for c in conn.execute("SELECT * FROM trusted_contacts WHERE user_id = ?", (user["id"],)).fetchall()
            ]

    return {
        "open_requests": open_requests,
        "my_trips": my_trips,
        "trusted_contacts": trusted_contacts,
        "minor_autonomous_enabled": False,
        "minor_policy_note": "Contratación autónoma por menores deshabilitada por defecto. Solo se muestra el flujo propuesto de adulta responsable solicitando viaje para menor acompañada.",
    }


@router.post("/requests")
def create_trip_request(payload: TripRequestIn, user: dict = Depends(require_adult)):
    if payload.minor_autonomous_attempt:
        raise HTTPException(
            status_code=403,
            detail="La contratación autónoma de viajes por menores de edad está deshabilitada en BERA. Edad mínima, acompañamiento y autorización están pendientes de definición.",
        )
    if payload.origin_comuna not in COMUNA_NAMES or payload.destination_comuna not in COMUNA_NAMES:
        raise HTTPException(status_code=400, detail="Origen y destino deben estar dentro de las 21 comunas de la Región de Ñuble.")
    if payload.payment_method not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Método de pago inválido.")
    if payload.trip_type not in ("inmediato", "programado"):
        raise HTTPException(status_code=400, detail="Tipo de viaje inválido.")
    if payload.trip_type == "programado" and not payload.scheduled_at:
        raise HTTPException(status_code=400, detail="Los viajes programados requieren fecha y hora.")

    km, mins = _estimate_route(payload.origin_comuna, payload.destination_comuna)
    created = now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=60)).replace(microsecond=0).isoformat()

    with db_session() as conn:
        cur = conn.execute(
            """
            INSERT INTO trip_requests (
                passenger_id, origin_comuna, origin_address_simulated, destination_comuna,
                destination_address_simulated, trip_type, scheduled_at, proposed_fare,
                payment_method, estimated_km, estimated_min, for_minor_demo, minor_label_simulated,
                status, expires_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'solicitado', ?, ?)
            """,
            (
                user["id"],
                payload.origin_comuna,
                payload.origin_address_simulated.strip(),
                payload.destination_comuna,
                payload.destination_address_simulated.strip(),
                payload.trip_type,
                payload.scheduled_at,
                payload.proposed_fare,
                payload.payment_method,
                km,
                mins,
                1 if payload.for_minor_demo else 0,
                payload.minor_label_simulated.strip()
                or ("Flujo propuesto: adulta responsable solicita viaje para menor acompañada (demo)" if payload.for_minor_demo else ""),
                expires,
                created,
            ),
        )
        req_id = cur.lastrowid

    return {
        "id": req_id,
        "estimated_km": km,
        "estimated_min": mins,
        "message": "Solicitud de viaje publicada para negociación dentro de BERA.",
    }


@router.post("/requests/{request_id}/proposals")
def create_proposal(request_id: int, payload: ProposalIn, user: dict = Depends(require_adult)):
    if payload.payment_method not in PAYMENT_METHODS:
        raise HTTPException(status_code=400, detail="Método de pago inválido.")

    created = now_iso()
    expires = (datetime.now(timezone.utc) + timedelta(minutes=45)).replace(microsecond=0).isoformat()

    with db_session() as conn:
        req = conn.execute("SELECT * FROM trip_requests WHERE id = ?", (request_id,)).fetchone()
        if not req:
            raise HTTPException(status_code=404, detail="Solicitud de viaje no encontrada.")
        if req["status"] in ("confirmado", "cerrado", "cancelado"):
            raise HTTPException(status_code=409, detail="Esta solicitud ya está cerrada o confirmada.")

        # Determinar si quien propone es conductora o la pasajera contraofertando
        drv = conn.execute("SELECT * FROM drivers WHERE user_id = ?", (user["id"],)).fetchone()
        if req["passenger_id"] == user["id"]:
            if not payload.driver_id:
                raise HTTPException(status_code=400, detail="Debes indicar a qué conductora envías la contraoferta.")
            proposer_role = "pasajera"
            driver_id = payload.driver_id
        else:
            if not drv or drv["approval_status"] != "aprobada" or not has_approved_verification(conn, user["id"], "conductora"):
                raise HTTPException(status_code=403, detail="Solo conductoras aprobadas y verificadas pueden enviar ofertas de tarifa.")
            proposer_role = "conductora"
            driver_id = drv["id"]

        # Marcar propuestas previas vigentes de esa misma dupla como superadas
        conn.execute(
            "UPDATE fare_proposals SET status = 'superada' WHERE trip_request_id = ? AND driver_id = ? AND status = 'vigente'",
            (request_id, driver_id),
        )
        cur = conn.execute(
            """
            INSERT INTO fare_proposals (trip_request_id, driver_id, proposer_role, amount, payment_method, note, status, expires_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'vigente', ?, ?)
            """,
            (request_id, driver_id, proposer_role, payload.amount, payload.payment_method, payload.note.strip(), expires, created),
        )
        conn.execute("UPDATE trip_requests SET status = 'en negociación' WHERE id = ?", (request_id,))

        target_user_id = req["passenger_id"] if proposer_role == "conductora" else conn.execute("SELECT user_id FROM drivers WHERE id = ?", (driver_id,)).fetchone()["user_id"]
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, 'Nueva propuesta de tarifa (Simulada)', ?, 'movilidad', 1, ?)",
            (target_user_id, f"Propuesta de ${payload.amount:,} ({payload.payment_method}) en solicitud #{request_id}.", created),
        )

    return {"id": cur.lastrowid, "message": "Propuesta de tarifa registrada."}


@router.post("/requests/{request_id}/proposals/{proposal_id}/accept")
def accept_proposal(request_id: int, proposal_id: int, user: dict = Depends(require_adult)):
    created = now_iso()
    with db_session() as conn:
        req = conn.execute("SELECT * FROM trip_requests WHERE id = ?", (request_id,)).fetchone()
        if not req:
            raise HTTPException(status_code=404, detail="Solicitud no encontrada.")
        if req["status"] in ("confirmado", "cerrado", "cancelado"):
            raise HTTPException(status_code=409, detail="La solicitud ya fue confirmada o cerrada. No se permiten confirmaciones duplicadas.")

        prop = conn.execute(
            "SELECT * FROM fare_proposals WHERE id = ? AND trip_request_id = ?",
            (proposal_id, request_id),
        ).fetchone()
        if not prop or prop["status"] != "vigente":
            raise HTTPException(status_code=409, detail="La propuesta no está vigente o ya fue superada.")
        if prop["expires_at"] < created:
            conn.execute("UPDATE fare_proposals SET status = 'vencida' WHERE id = ?", (proposal_id,))
            raise HTTPException(status_code=410, detail="La propuesta ha vencido.")

        drv = conn.execute("SELECT * FROM drivers WHERE id = ?", (prop["driver_id"],)).fetchone()
        # Quien acepta debe ser la contraparte
        if prop["proposer_role"] == "conductora" and req["passenger_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Solo la pasajera solicitante puede aceptar la oferta de la conductora.")
        if prop["proposer_role"] == "pasajera" and drv["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Solo la conductora destinataria puede aceptar la contraoferta.")

        # Evitar doble asignación simultánea en viajes inmediatos
        if req["trip_type"] == "inmediato":
            active_drv = conn.execute(
                "SELECT id FROM trips WHERE driver_id = ? AND trip_type = 'inmediato' AND status IN ('confirmado', 'conductora en camino', 'conductora en origen', 'en curso')",
                (drv["id"],),
            ).fetchone()
            if active_drv:
                raise HTTPException(status_code=409, detail="La conductora ya tiene otro viaje inmediato activo en curso.")

        # Evitar conflictos de horario en viajes programados (+/- 60 min)
        if req["trip_type"] == "programado" and req["scheduled_at"]:
            target_dt = datetime.fromisoformat(req["scheduled_at"].replace("Z", "+00:00"))
            sched_trips = conn.execute(
                "SELECT id, scheduled_at FROM trips WHERE driver_id = ? AND trip_type = 'programado' AND status NOT IN ('completado', 'cancelado') AND scheduled_at IS NOT NULL",
                (drv["id"],),
            ).fetchall()
            for st in sched_trips:
                st_dt = datetime.fromisoformat(st["scheduled_at"].replace("Z", "+00:00"))
                if abs((target_dt - st_dt).total_seconds()) < 3600:
                    raise HTTPException(
                        status_code=409,
                        detail="Conflicto de horario: la conductora tiene otro viaje programado dentro de una ventana de 60 minutos.",
                    )

        veh = conn.execute("SELECT * FROM vehicles WHERE driver_id = ? AND approval_status = 'aprobada' LIMIT 1", (drv["id"],)).fetchone()
        if not veh:
            raise HTTPException(status_code=400, detail="La conductora no tiene vehículo aprobado.")

        # Cerrar solicitud y vencer demás propuestas
        conn.execute("UPDATE fare_proposals SET status = 'aceptada' WHERE id = ?", (proposal_id,))
        conn.execute(
            "UPDATE fare_proposals SET status = 'vencida' WHERE trip_request_id = ? AND id != ? AND status = 'vigente'",
            (request_id, proposal_id),
        )
        conn.execute("UPDATE trip_requests SET status = 'cerrado' WHERE id = ?", (request_id,))

        pin = str(secrets.randbelow(9000) + 1000)
        t_cur = conn.execute(
            """
            INSERT INTO trips (
                trip_request_id, passenger_id, driver_id, vehicle_id, final_fare, payment_method,
                payment_status, trip_type, scheduled_at, status, start_pin, passenger_confirmed, driver_confirmed,
                simulated_progress, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'pendiente', ?, ?, 'confirmado', ?, 1, 1, 10, ?, ?)
            """,
            (
                request_id,
                req["passenger_id"],
                drv["id"],
                veh["id"],
                prop["amount"],
                prop["payment_method"],
                req["trip_type"],
                req["scheduled_at"],
                pin,
                created,
                created,
            ),
        )
        trip_id = t_cur.lastrowid

        # Crear conversación asociada al viaje
        conn.execute(
            "INSERT INTO conversations (context_type, context_id, participant_a_id, participant_b_id, created_at) VALUES ('trip', ?, ?, ?, ?)",
            (trip_id, req["passenger_id"], drv["user_id"], created),
        )

    return {"trip_id": trip_id, "start_pin": pin, "message": "Viaje confirmado con aceptación de ambas partes."}


@router.post("/trips/{trip_id}/status")
def update_trip_status(trip_id: int, payload: TripStatusIn, user: dict = Depends(require_user)):
    if payload.status not in TRIP_STATES:
        raise HTTPException(status_code=400, detail="Estado de viaje inválido.")
    progress_map = {
        "confirmado": 10,
        "conductora en camino": 35,
        "conductora en origen": 55,
        "en curso": 80,
        "completado": 100,
        "cancelado": 0,
    }
    with db_session() as conn:
        trip = conn.execute(
            "SELECT t.*, d.user_id AS driver_user_id FROM trips t JOIN drivers d ON d.id = t.driver_id WHERE t.id = ?",
            (trip_id,),
        ).fetchone()
        if not trip:
            raise HTTPException(status_code=404, detail="Viaje no encontrado.")
        if user["id"] not in (trip["passenger_id"], trip["driver_user_id"]):
            raise HTTPException(status_code=403, detail="No tienes permiso para modificar este viaje.")
        if trip["status"] in ("completado", "cancelado"):
            raise HTTPException(status_code=409, detail="El viaje ya finalizó o fue cancelado.")

        if payload.status in ("conductora en camino", "conductora en origen", "en curso", "completado") and user["id"] != trip["driver_user_id"]:
            raise HTTPException(status_code=403, detail="Solo la conductora asignada puede avanzar las etapas del recorrido.")

        conn.execute(
            "UPDATE trips SET status = ?, simulated_progress = ?, cancellation_reason = ?, updated_at = ? WHERE id = ?",
            (payload.status, progress_map.get(payload.status, 50), payload.cancellation_reason.strip(), now_iso(), trip_id),
        )
        if payload.status == "completado":
            conn.execute("UPDATE drivers SET trips_completed = trips_completed + 1 WHERE id = ?", (trip["driver_id"],))
    return {"message": f"Estado del viaje actualizado a '{payload.status}'."}


@router.post("/trips/{trip_id}/payment")
def simulate_payment(trip_id: int, payload: PaymentActionIn, user: dict = Depends(require_user)):
    with db_session() as conn:
        trip = conn.execute(
            "SELECT t.*, d.user_id AS driver_user_id FROM trips t JOIN drivers d ON d.id = t.driver_id WHERE t.id = ?",
            (trip_id,),
        ).fetchone()
        if not trip:
            raise HTTPException(status_code=404, detail="Viaje no encontrado.")
        if user["id"] not in (trip["passenger_id"], trip["driver_user_id"]):
            raise HTTPException(status_code=403, detail="Sin permiso sobre este viaje.")

        if payload.action == "declarar_pasajera":
            new_status = "declarado_pasajera"
            msg = "Pago declarado por la pasajera (simulación sin operación financiera real)."
        elif payload.action == "confirmar_simulado":
            new_status = "confirmado_simulado"
            msg = (
                "Pago confirmado en entorno simulado de BERA (sin tarjeta ni transferencia real)."
                if trip["payment_method"] == "pago_bera"
                else "Recepción de pago declarada por conductora (simulado)."
            )
        else:
            raise HTTPException(status_code=400, detail="Acción de pago inválida.")

        conn.execute("UPDATE trips SET payment_status = ?, updated_at = ? WHERE id = ?", (new_status, now_iso(), trip_id))
    return {"payment_status": new_status, "message": msg}


@router.post("/trips/{trip_id}/share")
def create_share_link(trip_id: int, user: dict = Depends(require_user)):
    token = secrets.token_urlsafe(18)
    expires = (datetime.now(timezone.utc) + timedelta(minutes=120)).replace(microsecond=0).isoformat()
    with db_session() as conn:
        trip = conn.execute("SELECT passenger_id FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if not trip or trip["passenger_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Solo la pasajera puede compartir su viaje.")
        conn.execute(
            "UPDATE trips SET share_token = ?, share_expires_at = ?, share_revoked = 0 WHERE id = ?",
            (token, expires, trip_id),
        )
    return {"share_token": token, "expires_at": expires, "share_url": f"/api/mobility/shared/{token}"}


@router.post("/trips/{trip_id}/revoke-share")
def revoke_share_link(trip_id: int, user: dict = Depends(require_user)):
    with db_session() as conn:
        trip = conn.execute("SELECT passenger_id FROM trips WHERE id = ?", (trip_id,)).fetchone()
        if not trip or trip["passenger_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Solo la pasajera puede revocar el enlace.")
        conn.execute("UPDATE trips SET share_revoked = 1 WHERE id = ?", (trip_id,))
    return {"message": "Enlace compartido revocado."}


@router.get("/shared/{token}")
def view_shared_trip(token: str):
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT t.id, t.status, t.simulated_progress, t.share_expires_at, t.share_revoked,
                   tr.origin_comuna, tr.destination_comuna, du.full_name AS driver_name,
                   v.brand_model, v.color, v.plate_simulated
            FROM trips t
            JOIN trip_requests tr ON tr.id = t.trip_request_id
            JOIN drivers d ON d.id = t.driver_id
            JOIN users du ON du.id = d.user_id
            JOIN vehicles v ON v.id = t.vehicle_id
            WHERE t.share_token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Enlace compartido inválido.")
        if row["share_revoked"]:
            raise HTTPException(status_code=410, detail="Este enlace compartido fue revocado por la pasajera.")
        if row["share_expires_at"] < now_iso():
            raise HTTPException(status_code=410, detail="Este enlace compartido ha caducado.")
        return {
            "simulated_tracking": True,
            "notice": "Seguimiento simulado de demostración. No expone ubicación GPS real.",
            "trip": dict(row),
        }


@router.post("/trusted-contacts")
def add_trusted_contact(payload: TrustedContactIn, user: dict = Depends(require_user)):
    with db_session() as conn:
        cur = conn.execute(
            "INSERT INTO trusted_contacts (user_id, name, relation, phone_simulated, created_at) VALUES (?, ?, ?, ?, ?)",
            (user["id"], payload.name.strip(), payload.relation.strip(), payload.phone_simulated.strip(), now_iso()),
        )
    return {"id": cur.lastrowid, "message": "Contacto de confianza ficticio guardado."}


@router.post("/help-test")
def trigger_help_test(user: dict = Depends(require_user)):
    with db_session() as conn:
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, 'Botón de ayuda (Prueba)', 'Se abrió el flujo de ayuda de demostración. No se realizaron llamadas a emergencias ni envíos a terceros.', 'seguridad', 1, ?)",
            (user["id"], now_iso()),
        )
    return {
        "simulated": True,
        "message": "Flujo de ayuda de prueba activado. En esta demostración no se contacta a emergencias ni se envían alertas externas.",
    }
