"""FastAPI entrypoint: API routes, CORS, and optional static hosting of the React build."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(title="Pricing Simulator", version="0.1.0")

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")


@app.get("/api/health")
def health() -> dict[str, str]:
    """Liveness probe for load balancers and local checks."""
    return {"status": "ok"}


static_dir = settings.static_dir
if static_dir and Path(static_dir).is_dir():
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
