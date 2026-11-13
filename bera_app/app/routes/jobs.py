"""
Módulo de Empleabilidad de BERA:
- Ofertas publicadas solo por mujeres empleadoras o empresas con representante verificada
- Moderación previa obligatoria antes de publicar
- Filtros por comuna, rubro, modalidad, jornada, flexibilidad, sin experiencia, remuneración, contrato
- Protección estricta de antecedentes de postulantes (cada empleadora solo ve postulaciones a sus ofertas)
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from ..config import APPLICATION_STATES, COMUNA_NAMES
from ..database import db_session
from ..security import get_optional_user, has_approved_verification, now_iso, require_adult

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class JobOfferIn(BaseModel):
    title: str = Field(..., min_length=4, max_length=120)
    rubro: str = Field(..., min_length=2, max_length=60)
    comuna: str
    modality: str  # presencial | remota | híbrida
    schedule_type: str  # full-time | part-time | por turnos
    flexible_hours: bool = False
    experience_required: bool = False
    salary_clp: int | None = None
    salary_note: str = "No informada"
    contract_type: str
    description: str = Field(..., min_length=10, max_length=1200)
    tasks: str = Field(..., min_length=5, max_length=800)
    requirements: str = Field(..., min_length=5, max_length=800)
    closing_date: str


class ApplyIn(BaseModel):
    cover_note: str = Field(..., min_length=5, max_length=600)


class ApplicationStatusIn(BaseModel):
    status: str


@router.get("")
def list_jobs(
    comuna: str | None = None,
    rubro: str | None = None,
    modality: str | None = None,
    schedule_type: str | None = None,
    flexible_hours: bool | None = None,
    no_experience: bool | None = None,
    contract_type: str | None = None,
    min_salary: int | None = None,
    q: str | None = None,
    user: dict | None = Depends(get_optional_user),
):
    clauses = ["j.moderation_status = 'aprobada'"]
    params = []

    if comuna:
        clauses.append("j.comuna = ?")
        params.append(comuna)
    if rubro:
        clauses.append("j.rubro = ?")
        params.append(rubro)
    if modality:
        clauses.append("j.modality = ?")
        params.append(modality)
    if schedule_type:
        clauses.append("j.schedule_type = ?")
        params.append(schedule_type)
    if flexible_hours:
        clauses.append("j.flexible_hours = 1")
    if no_experience:
        clauses.append("j.experience_required = 0")
    if contract_type:
        clauses.append("j.contract_type = ?")
        params.append(contract_type)
    if min_salary is not None:
        clauses.append("j.salary_clp >= ?")
        params.append(min_salary)
    if q:
        clauses.append("(j.title LIKE ? OR j.description LIKE ? OR j.rubro LIKE ?)")
        like = f"%{q.strip()}%"
        params.extend([like, like, like])

    sql = f"""
        SELECT j.*, u.full_name AS employer_name, c.name AS company_name
        FROM job_offers j
        JOIN users u ON u.id = j.employer_user_id
        LEFT JOIN companies c ON c.id = j.company_id
        WHERE {' AND '.join(clauses)}
        ORDER BY j.id DESC
    """
    with db_session() as conn:
        jobs = [dict(r) for r in conn.execute(sql, params).fetchall()]
        my_apps = []
        my_offers = []
        if user:
            my_apps = [
                dict(a)
                for a in conn.execute(
                    """
                    SELECT ja.*, jo.title AS job_title, jo.comuna
                    FROM job_applications ja
                    JOIN job_offers jo ON jo.id = ja.job_id
                    WHERE ja.applicant_user_id = ?
                    ORDER BY ja.id DESC
                    """,
                    (user["id"],),
                ).fetchall()
            ]
            my_offers = [
                dict(o)
                for o in conn.execute(
                    "SELECT * FROM job_offers WHERE employer_user_id = ? ORDER BY id DESC",
                    (user["id"],),
                ).fetchall()
            ]

    return {"jobs": jobs, "my_applications": my_apps, "my_offers": my_offers}


@router.post("")
def create_job(payload: JobOfferIn, user: dict = Depends(require_adult)):
    if payload.comuna not in COMUNA_NAMES:
        raise HTTPException(status_code=400, detail="Comuna fuera de la Región de Ñuble.")
    if payload.modality not in ("presencial", "remota", "híbrida"):
        raise HTTPException(status_code=400, detail="Modalidad inválida.")

    with db_session() as conn:
        is_verified_employer = (
            has_approved_verification(conn, user["id"], "empleadora")
            or has_approved_verification(conn, user["id"], "empresa")
            or has_approved_verification(conn, user["id"], "emprendedora")
        )
        if not is_verified_employer:
            raise HTTPException(
                status_code=403,
                detail="Solo mujeres empleadoras verificadas o empresas con representante verificada pueden publicar ofertas laborales.",
            )
        comp = conn.execute("SELECT id, authorization_status FROM companies WHERE representative_user_id = ?", (user["id"],)).fetchone()
        comp_id = comp["id"] if comp and comp["authorization_status"] == "aprobada" else None

        cur = conn.execute(
            """
            INSERT INTO job_offers (
                employer_user_id, company_id, title, rubro, comuna, modality, schedule_type,
                flexible_hours, experience_required, salary_clp, salary_note, contract_type,
                description, tasks, requirements, closing_date, application_method,
                moderation_status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Postulación en BERA', 'pendiente', ?)
            """,
            (
                user["id"],
                comp_id,
                payload.title.strip(),
                payload.rubro.strip(),
                payload.comuna,
                payload.modality,
                payload.schedule_type,
                1 if payload.flexible_hours else 0,
                1 if payload.experience_required else 0,
                payload.salary_clp,
                payload.salary_note.strip() or ("No informada" if payload.salary_clp is None else f"${payload.salary_clp:,}"),
                payload.contract_type,
                payload.description.strip(),
                payload.tasks.strip(),
                payload.requirements.strip(),
                payload.closing_date,
                now_iso(),
            ),
        )
    return {
        "id": cur.lastrowid,
        "moderation_status": "pendiente",
        "message": "Oferta laboral enviada a revisión administrativa antes de su publicación.",
    }


@router.post("/{job_id}/apply")
def apply_to_job(job_id: int, payload: ApplyIn, user: dict = Depends(require_adult)):
    created = now_iso()
    with db_session() as conn:
        job = conn.execute("SELECT * FROM job_offers WHERE id = ? AND moderation_status = 'aprobada'", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Oferta laboral no disponible.")
        if job["employer_user_id"] == user["id"]:
            raise HTTPException(status_code=400, detail="No puedes postular a tu propia oferta.")
        existing = conn.execute(
            "SELECT id, status FROM job_applications WHERE job_id = ? AND applicant_user_id = ?",
            (job_id, user["id"]),
        ).fetchone()
        if existing and existing["status"] != "retirada":
            raise HTTPException(status_code=409, detail="Ya postulaste a esta oferta.")

        cv_snap = f"{user['full_name']} ({user['comuna']}) — {user.get('cv_summary') or 'Perfil básico BERA'} | Habilidades: {user.get('cv_skills') or 'No especificadas'}"
        if existing:
            conn.execute(
                "UPDATE job_applications SET cover_note = ?, cv_snapshot = ?, status = 'enviada', updated_at = ? WHERE id = ?",
                (payload.cover_note.strip(), cv_snap, created, existing["id"]),
            )
            app_id = existing["id"]
        else:
            cur = conn.execute(
                "INSERT INTO job_applications (job_id, applicant_user_id, cover_note, cv_snapshot, status, created_at, updated_at) VALUES (?, ?, ?, ?, 'enviada', ?, ?)",
                (job_id, user["id"], payload.cover_note.strip(), cv_snap, created, created),
            )
            app_id = cur.lastrowid
    return {"id": app_id, "status": "enviada", "message": "Postulación enviada."}


@router.post("/applications/{app_id}/withdraw")
def withdraw_application(app_id: int, user: dict = Depends(require_adult)):
    with db_session() as conn:
        app = conn.execute("SELECT * FROM job_applications WHERE id = ?", (app_id,)).fetchone()
        if not app or app["applicant_user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="No puedes retirar esta postulación.")
        conn.execute("UPDATE job_applications SET status = 'retirada', updated_at = ? WHERE id = ?", (now_iso(), app_id))
    return {"message": "Postulación retirada."}


@router.get("/{job_id}/applications")
def get_job_applications(job_id: int, user: dict = Depends(require_adult)):
    with db_session() as conn:
        job = conn.execute("SELECT * FROM job_offers WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(status_code=404, detail="Oferta no encontrada.")
        if job["employer_user_id"] != user["id"]:
            raise HTTPException(
                status_code=403,
                detail="Acceso denegado: cada empleadora solo puede ver postulaciones de sus propias ofertas.",
            )
        rows = conn.execute(
            """
            SELECT ja.*, u.full_name AS applicant_name, u.comuna AS applicant_comuna
            FROM job_applications ja
            JOIN users u ON u.id = ja.applicant_user_id
            WHERE ja.job_id = ? AND ja.status != 'retirada'
            ORDER BY ja.id DESC
            """,
            (job_id,),
        ).fetchall()
    return {"applications": [dict(r) for r in rows]}


@router.post("/applications/{app_id}/status")
def update_application_status(app_id: int, payload: ApplicationStatusIn, user: dict = Depends(require_adult)):
    if payload.status not in APPLICATION_STATES:
        raise HTTPException(status_code=400, detail="Estado de postulación inválido.")
    with db_session() as conn:
        row = conn.execute(
            """
            SELECT ja.*, jo.employer_user_id, jo.title
            FROM job_applications ja
            JOIN job_offers jo ON jo.id = ja.job_id
            WHERE ja.id = ?
            """,
            (app_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Postulación no encontrada.")
        if row["employer_user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="Solo la empleadora dueña de la oferta puede actualizar el estado.")
        conn.execute(
            "UPDATE job_applications SET status = ?, updated_at = ? WHERE id = ?",
            (payload.status, now_iso(), app_id),
        )
        conn.execute(
            "INSERT INTO notifications (user_id, title, body, category, is_simulated, created_at) VALUES (?, 'Actualización de postulación (Simulada)', ?, 'empleos', 1, ?)",
            (row["applicant_user_id"], f"Tu postulación a '{row['title']}' pasó a estado: {payload.status}.", now_iso()),
        )
    return {"message": f"Estado actualizado a '{payload.status}'."}
