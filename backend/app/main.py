"""
Aether Backend - FastAPI Application Entrypoint

Stage 4: wires up the database (init_db) and the first real route,
POST /api/agent/init, on top of the Stage 1 skeleton.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.routes import agent as agent_routes
from app.services.scheduler import stop_scheduler

# Configure standard logging to output INFO level logs to stdout (for Railway)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

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
    """Create tables if they don't exist yet, and resume scheduler if an agent is active."""
    init_db()
    
    # Auto-resume scheduler on app boot if an agent already exists
    try:
        from app.core.database import SessionLocal
        from app.models.agent import Agent
        from app.services.scheduler import start_scheduler
        
        db = SessionLocal()
        try:
            agent = db.query(Agent).order_by(Agent.created_at.desc()).first()
            if agent:
                logging.info(f"on_startup: Resuming scheduler for active agent {agent.id}")
                start_scheduler(agent.id)
        finally:
            db.close()
    except Exception as exc:
        logging.warning(f"on_startup: Could not auto-resume scheduler: {exc}")


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
