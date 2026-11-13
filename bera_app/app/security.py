"""
Seguridad, hashing de contraseñas, sesiones, permisos en servidor y limitación de tasa.
"""
import hashlib
import hmac
import json
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from fastapi import Depends, Header, HTTPException, Request, status
from .config import RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SEC, SECRET_KEY, SESSION_TTL_HOURS
from .database import db_session

_RATE_BUCKETS = defaultdict(list)


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"pbkdf2_sha256${salt}${dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        algo, salt, hex_digest = stored_hash.split("$", 2)
        if algo != "pbkdf2_sha256":
            return False
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
        return hmac.compare_digest(dk.hex(), hex_digest)
    except Exception:
        return False


def check_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "local"
    now = time.time()
    bucket = _RATE_BUCKETS[client_ip]
    cutoff = now - RATE_LIMIT_WINDOW_SEC
    _RATE_BUCKETS[client_ip] = [ts for ts in bucket if ts > cutoff]
    if len(_RATE_BUCKETS[client_ip]) >= RATE_LIMIT_MAX_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiadas solicitudes. Intenta nuevamente en unos segundos.",
        )
    _RATE_BUCKETS[client_ip].append(now)


def create_session(user_id: int, db_path: str = None) -> str:
    raw = secrets.token_urlsafe(32)
    sig = hmac.new(SECRET_KEY.encode("utf-8"), raw.encode("utf-8"), hashlib.sha256).hexdigest()[:16]
    token = f"{raw}.{sig}"
    created = datetime.now(timezone.utc)
    expires = created + timedelta(hours=SESSION_TTL_HOURS)
    with db_session(db_path) as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (token, user_id, expires.replace(microsecond=0).isoformat(), created.replace(microsecond=0).isoformat()),
        )
    return token


def _parse_user_row(row) -> dict:
    if not row:
        return None
    d = dict(row)
    d["roles"] = json.loads(d.get("roles_json") or "[]")
    d["admin_permissions"] = json.loads(d.get("admin_permissions_json") or "[]")
    d["privacy_settings"] = json.loads(d.get("privacy_settings_json") or "{}")
    d.pop("password_hash", None)
    return d


def get_optional_user(
    request: Request,
    authorization: str = Header(default=None),
) -> dict | None:
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
    elif request.cookies.get("bera_session"):
        token = request.cookies.get("bera_session")

    if not token:
        return None

    with db_session() as conn:
        row = conn.execute(
            """
            SELECT u.*, s.expires_at
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token = ?
            """,
            (token,),
        ).fetchone()
        if not row:
            return None
        if row["expires_at"] < now_iso():
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None
        user = _parse_user_row(row)
        if user["account_status"] == "suspendida":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cuenta suspendida por administración. Puedes presentar una apelación.",
            )
        return user


def require_user(user: dict | None = Depends(get_optional_user)) -> dict:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Debes iniciar sesión para realizar esta acción. Las invitadas solo pueden explorar contenido público.",
        )
    return user


def require_adult(user: dict = Depends(require_user)) -> dict:
    if not user.get("is_adult"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta función requiere ser mayor de 18 años.",
        )
    return user


def require_admin_permission(permission: str):
    def _checker(user: dict = Depends(require_user)) -> dict:
        if "admin" not in user.get("roles", []) and not user.get("admin_level"):
            raise HTTPException(status_code=403, detail="Acceso restringido a administración.")
        perms = user.get("admin_permissions", [])
        if "*" not in perms and permission not in perms:
            raise HTTPException(
                status_code=403,
                detail=f"Tu cuenta de administración no tiene permiso para: {permission}.",
            )
        return user

    return _checker


def has_approved_verification(conn, user_id: int, scope: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM verifications WHERE user_id = ? AND scope = ? AND status = 'aprobada' LIMIT 1",
        (user_id, scope),
    ).fetchone()
    return row is not None
