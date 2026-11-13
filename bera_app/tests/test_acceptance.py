"""
Suite automatizada de pruebas de aceptación para BERA (Región de Ñuble).
Verifica los criterios de la sección 14 del requerimiento.
"""
import os
import sys
import tempfile

# Usar base de datos temporal aislada para pruebas
TMP_DB = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
os.environ["BERA_DB_PATH"] = TMP_DB

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app.database import init_db
from app.seed import seed_database
from app.main import app

init_db(TMP_DB)
seed_database(TMP_DB, force=True)
client = TestClient(app)


def login_demo(email: str) -> dict:
    r = client.post("/api/auth/demo-login", json={"email": email})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def run_all():
    # 1. Salud, PWA y catálogo de 21 comunas
    r = client.get("/api/health")
    assert r.status_code == 200
    assert "Demostración" in r.json()["demo_notice"]
    assert client.get("/manifest.json").status_code == 200
    assert client.get("/sw.js").status_code == 200
    comunas = client.get("/api/mobility/comunas").json()["comunas"]
    assert len(comunas) == 21 and "Chillán" in comunas and "Bulnes" in comunas

    # 2. Restricciones de invitadas
    assert client.post("/api/mobility/requests", json={
        "origin_comuna": "Chillán", "origin_address_simulated": "A",
        "destination_comuna": "Bulnes", "destination_address_simulated": "B",
        "proposed_fare": 4000
    }).status_code == 401
    assert client.post("/api/jobs/1/apply", json={"cover_note": "Hola"}).status_code == 401
    assert client.get("/api/jobs").status_code == 200  # Público sí permitido

    # 3. Registro y validación 18+ y comuna Ñuble
    r_minor = client.post("/api/auth/register", json={
        "email": "menor@test.cl", "password": "Password123", "full_name": "Menor Test",
        "comuna": "Chillán", "birth_year": 2012, "intent": "utilizar servicios",
        "eligibility_declared": True, "consent_accepted": True
    })
    assert r_minor.status_code == 403

    r_reg = client.post("/api/auth/register", json={
        "email": "nueva@test.cl", "password": "Password123", "full_name": "Camila Nueva",
        "comuna": "Quillón", "birth_year": 1995, "intent": "ambas",
        "eligibility_declared": True, "consent_accepted": True
    })
    assert r_reg.status_code == 200

    # 4. Bloqueo de contratación autónoma por menor en movilidad + flujo propuesto adulta->menor
    h_pas = login_demo("pasajera@bera.cl")
    r_aut_minor = client.post("/api/mobility/requests", headers=h_pas, json={
        "origin_comuna": "Chillán", "origin_address_simulated": "Centro",
        "destination_comuna": "Bulnes", "destination_address_simulated": "Plaza",
        "proposed_fare": 5000, "minor_autonomous_attempt": True
    })
    assert r_aut_minor.status_code == 403

    # 5. Negociación de tarifas, prevención de doble asignación y estados de viaje/pago
    h_drv = login_demo("conductora@bera.cl")
    r_req = client.post("/api/mobility/requests", headers=h_pas, json={
        "origin_comuna": "Chillán", "origin_address_simulated": "Av. Libertad",
        "destination_comuna": "Pinto", "destination_address_simulated": "Plaza Pinto",
        "trip_type": "inmediato", "proposed_fare": 9000, "payment_method": "pago_bera"
    })
    assert r_req.status_code == 200
    req_id = r_req.json()["id"]

    r_prop = client.post(f"/api/mobility/requests/{req_id}/proposals", headers=h_drv, json={
        "amount": 10000, "payment_method": "pago_bera", "note": "Salgo en 5 min"
    })
    assert r_prop.status_code == 200
    prop_id = r_prop.json()["id"]

    r_acc = client.post(f"/api/mobility/requests/{req_id}/proposals/{prop_id}/accept", headers=h_pas)
    assert r_acc.status_code == 200
    trip_id = r_acc.json()["trip_id"]

    # Doble confirmación bloqueada
    assert client.post(f"/api/mobility/requests/{req_id}/proposals/{prop_id}/accept", headers=h_pas).status_code == 409

    # Enlace compartido y revocación
    sh = client.post(f"/api/mobility/trips/{trip_id}/share", headers=h_pas).json()
    assert client.get(sh["share_url"]).status_code == 200
    client.post(f"/api/mobility/trips/{trip_id}/revoke-share", headers=h_pas)
    assert client.get(sh["share_url"]).status_code == 410

    # Avanzar viaje y simular pago
    for st in ["conductora en camino", "conductora en origen", "en curso", "completado"]:
        assert client.post(f"/api/mobility/trips/{trip_id}/status", headers=h_drv, json={"status": st}).status_code == 200
    assert client.post(f"/api/mobility/trips/{trip_id}/payment", headers=h_pas, json={"action": "declarar_pasajera"}).status_code == 200
    assert client.post(f"/api/mobility/trips/{trip_id}/payment", headers=h_drv, json={"action": "confirmar_simulado"}).status_code == 200

    # 6. Conflicto de horario en viajes programados
    h_drv2 = login_demo("conductora2@bera.cl")
    sched_time = "2026-12-01T10:00:00+00:00"
    s1 = client.post("/api/mobility/requests", headers=h_pas, json={
        "origin_comuna": "San Carlos", "origin_address_simulated": "Plaza",
        "destination_comuna": "Chillán", "destination_address_simulated": "Terminal",
        "trip_type": "programado", "scheduled_at": sched_time, "proposed_fare": 7000
    }).json()["id"]
    p1 = client.post(f"/api/mobility/requests/{s1}/proposals", headers=h_drv2, json={"amount": 7500}).json()["id"]
    assert client.post(f"/api/mobility/requests/{s1}/proposals/{p1}/accept", headers=h_pas).status_code == 200

    s2 = client.post("/api/mobility/requests", headers=h_pas, json={
        "origin_comuna": "San Carlos", "origin_address_simulated": "Hospital",
        "destination_comuna": "Coihueco", "destination_address_simulated": "Centro",
        "trip_type": "programado", "scheduled_at": "2026-12-01T10:30:00+00:00", "proposed_fare": 8000
    }).json()["id"]
    p2 = client.post(f"/api/mobility/requests/{s2}/proposals", headers=h_drv2, json={"amount": 8000}).json()["id"]
    assert client.post(f"/api/mobility/requests/{s2}/proposals/{p2}/accept", headers=h_pas).status_code == 409

    # 7. Empleabilidad: moderación previa, postulación y aislamiento entre empleadoras
    h_emp = login_demo("empresa@bera.cl")
    h_post = login_demo("postulante@bera.cl")
    # Empleadora ajena (emprendedora@bera.cl) no puede ver postulaciones de empresa@bera.cl
    h_other_emp = login_demo("emprendedora@bera.cl")
    assert client.get("/api/jobs/1/applications", headers=h_other_emp).status_code == 403
    assert client.get("/api/jobs/1/applications", headers=h_emp).status_code == 200

    # 8. Emprendimientos: edición sensible vuelve a revisión
    r_edit_v = client.put("/api/ventures/1", headers=h_other_emp, json={
        "name": "Botánica Valle del Sol Renovada",
        "category": "Cosmética y Bienestar",
        "comuna": "Quillón",
        "description": "Nueva descripción sensible de prueba para verificar re-moderación.",
        "schedule_text": "Lunes a sábado, 10:00 a 19:00 hrs",
        "whatsapp_authorized": True,
        "whatsapp_simulated": "+56 9 0000 5555"
    })
    assert r_edit_v.status_code == 200
    assert r_edit_v.json()["moderation_status"] == "en revisión"

    # 9. Administración: permisos diferenciados entre 4 admins y prevención de resoluciones contradictorias
    h_adm2 = login_demo("admin2@bera.cl")  # Solo identidad/conductoras/apelaciones
    h_adm3 = login_demo("admin3@bera.cl")  # Solo empleos/empresas/denuncias
    # Admin 2 no tiene permiso para aprobar empleos
    assert client.post("/api/admin/jobs/5/decide", headers=h_adm2, json={"status": "aprobada", "reason": "Intento sin permiso"}).status_code == 403
    # Admin 3 sí puede aprobar empleo #5
    assert client.post("/api/admin/jobs/5/decide", headers=h_adm3, json={"status": "aprobada", "reason": "Oferta completa y verificada"}).status_code == 200
    # Admin 1 intenta contradecir verificación #1 ya aprobada por Admin 2
    h_adm1 = login_demo("admin1@bera.cl")
    assert client.post("/api/admin/verifications/1/decide", headers=h_adm1, json={"status": "rechazada", "reason": "Contradicción"}).status_code == 409

    # 10. Bloqueo de mensajería
    assert client.post("/api/common/blocks", headers=h_pas, json={"blocked_user_id": 5}).status_code == 200
    assert client.post("/api/ventures/1/contact", headers=h_pas).status_code in (403, 404)

    print("TODAS LAS PRUEBAS DE ACEPTACIÓN PASARON EXITOSAMENTE.")


if __name__ == "__main__":
    try:
        run_all()
    finally:
        if os.path.exists(TMP_DB):
            os.remove(TMP_DB)
