"""
Configuración central de BERA (Demostración Funcional - Región de Ñuble, Chile).
"""
import os

APP_NAME = "BERA"
APP_SLOGAN = "Conectadas para avanzar"
DEMO_NOTICE = "Demostración: no coordina viajes ni procesa pagos reales"

SECRET_KEY = os.environ.get("BERA_SECRET_KEY", "bera-demo-dev-secret-change-in-production")
DB_PATH = os.environ.get(
    "BERA_DB_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "bera.db"),
)
SESSION_TTL_HOURS = int(os.environ.get("BERA_SESSION_TTL_HOURS", "24"))
RATE_LIMIT_MAX_REQUESTS = int(os.environ.get("BERA_RATE_LIMIT_MAX", "120"))
RATE_LIMIT_WINDOW_SEC = int(os.environ.get("BERA_RATE_LIMIT_WINDOW", "60"))

# Proveedores externos (en demostración permanecen deshabilitados / simulados)
GOOGLE_OAUTH_ENABLED = bool(os.environ.get("BERA_GOOGLE_CLIENT_ID"))
EMAIL_PROVIDER_ENABLED = bool(os.environ.get("BERA_SMTP_HOST"))
PAYMENT_PROVIDER_ENABLED = bool(os.environ.get("BERA_PAYMENT_API_KEY"))

# Catálogo oficial verificado de las 21 comunas de la Región de Ñuble (Ley 21.033 / BCN)
# Incluye coordenadas aproximadas de cabecera comunal solo para estimación simulada de distancia/duración.
NUBLE_COMUNAS = [
    {"nombre": "Chillán", "provincia": "Diguillín", "lat": -36.6066, "lng": -72.1034},
    {"nombre": "Chillán Viejo", "provincia": "Diguillín", "lat": -36.6228, "lng": -72.1319},
    {"nombre": "Bulnes", "provincia": "Diguillín", "lat": -36.7423, "lng": -72.2985},
    {"nombre": "El Carmen", "provincia": "Diguillín", "lat": -36.8981, "lng": -72.0236},
    {"nombre": "Pemuco", "provincia": "Diguillín", "lat": -36.9769, "lng": -72.1047},
    {"nombre": "Pinto", "provincia": "Diguillín", "lat": -36.6975, "lng": -71.8944},
    {"nombre": "Quillón", "provincia": "Diguillín", "lat": -36.7436, "lng": -72.4706},
    {"nombre": "San Ignacio", "provincia": "Diguillín", "lat": -36.8011, "lng": -72.0331},
    {"nombre": "Yungay", "provincia": "Diguillín", "lat": -37.1219, "lng": -72.0128},
    {"nombre": "San Carlos", "provincia": "Punilla", "lat": -36.4247, "lng": -71.9581},
    {"nombre": "Coihueco", "provincia": "Punilla", "lat": -36.6281, "lng": -71.8322},
    {"nombre": "Ñiquén", "provincia": "Punilla", "lat": -36.2897, "lng": -71.8994},
    {"nombre": "San Fabián", "provincia": "Punilla", "lat": -36.5553, "lng": -71.5478},
    {"nombre": "San Nicolás", "provincia": "Punilla", "lat": -36.5017, "lng": -72.2122},
    {"nombre": "Quirihue", "provincia": "Itata", "lat": -36.2833, "lng": -72.5333},
    {"nombre": "Cobquecura", "provincia": "Itata", "lat": -36.1333, "lng": -72.7833},
    {"nombre": "Coelemu", "provincia": "Itata", "lat": -36.4875, "lng": -72.6997},
    {"nombre": "Ninhue", "provincia": "Itata", "lat": -36.4036, "lng": -72.3983},
    {"nombre": "Portezuelo", "provincia": "Itata", "lat": -36.5297, "lng": -72.4317},
    {"nombre": "Ránquil", "provincia": "Itata", "lat": -36.6333, "lng": -72.5667},
    {"nombre": "Treguaco", "provincia": "Itata", "lat": -36.4333, "lng": -72.6667},
]

COMUNA_NAMES = [c["nombre"] for c in NUBLE_COMUNAS]
COMUNA_MAP = {c["nombre"]: c for c in NUBLE_COMUNAS}

VERIFICATION_STATES = ["pendiente", "en revisión", "aprobada", "rechazada", "vencida"]
TRIP_STATES = [
    "solicitado",
    "en negociación",
    "confirmado",
    "conductora en camino",
    "conductora en origen",
    "en curso",
    "completado",
    "cancelado",
]
APPLICATION_STATES = ["enviada", "en revisión", "preseleccionada", "seleccionada", "no seleccionada"]
PAYMENT_METHODS = ["efectivo", "transferencia", "pago_bera"]
