"""
Punto de entrada principal de BERA (FastAPI + PWA).
"""
import os
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from .config import APP_NAME, APP_SLOGAN, DEMO_NOTICE
from .database import init_db
from .routes import admin, auth, common, jobs, mobility, ventures
from .seed import seed_database
from .security import check_rate_limit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI(title=f"{APP_NAME} — {APP_SLOGAN}", version="1.0.0-demo")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        check_rate_limit(request)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    return response


@app.on_event("startup")
def on_startup():
    init_db()
    seed_database()


app.include_router(auth.router)
app.include_router(mobility.router)
app.include_router(jobs.router)
app.include_router(ventures.router)
app.include_router(common.router)
app.include_router(admin.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": APP_NAME, "slogan": APP_SLOGAN, "demo_notice": DEMO_NOTICE}


@app.get("/manifest.json")
def manifest():
    return FileResponse(os.path.join(STATIC_DIR, "manifest.json"), media_type="application/manifest+json")


@app.get("/sw.js")
def service_worker():
    return FileResponse(os.path.join(STATIC_DIR, "sw.js"), media_type="application/javascript")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/{full_path:path}")
def spa_fallback(full_path: str):
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))
