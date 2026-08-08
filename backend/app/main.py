"""
Aether Backend - FastAPI Application Entrypoint

Stage 1: Skeleton only. No agent logic yet.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings

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


@app.get("/api/health")
def health_check():
    """Basic liveness check used to confirm the service is up on Railway."""
    return {
        "status": "ok",
        "app": "aether-backend",
        "env": settings.app_env,
    }
