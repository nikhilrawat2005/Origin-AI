"""
Aether Backend - FastAPI Application Entrypoint

Stage 4: wires up the database (init_db) and the first real route,
POST /api/agent/init, on top of the Stage 1 skeleton.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.routes import agent as agent_routes
from app.services.scheduler import stop_scheduler

# Import models package so every model is registered on Base.metadata
# before init_db() creates tables (see app/models/__init__.py).
import app.models  # noqa: F401

settings = get_settings()

app = FastAPI(
    title="Aether API",
    description="Autonomous AI Technology Research Persona - Backend",
    version="0.1.0",
)

# CORS: allow the Next.js frontend to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tightened later if needed; no auth in scope per PRD
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    """Create tables if they don't exist yet. Safe to call every boot —
    create_all() is a no-op for tables that already exist."""
    init_db()


@app.on_event("shutdown")
def on_shutdown():
    """Stop the Stage 18 scheduler cleanly, if it was ever started —
    matters most for local dev auto-reload, so a killed/restarted
    process doesn't leave an orphaned background thread behind."""
    stop_scheduler()


app.include_router(agent_routes.router)


@app.get("/api/health")
def health_check():
    """Basic liveness check used to confirm the service is up on Railway."""
    return {
        "status": "ok",
        "app": "aether-backend",
        "env": settings.app_env,
    }
