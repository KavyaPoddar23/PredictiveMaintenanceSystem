
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.app.api.predictions import router as predictions_router


ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = ROOT / "frontend"


app = FastAPI(
    title="Industrial Predictive Maintenance API",
    description=(
        "Predictive maintenance platform for industrial "
        "machine failure risk monitoring."
    ),
    version="1.0.0"
)


app.include_router(predictions_router)


app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static"
)


@app.get("/")
def root():
    return {
        "message": "Industrial Predictive Maintenance API",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/health"
    }


@app.get("/dashboard", include_in_schema=False)
def dashboard():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "service": "industrial-predictive-maintenance"
    }
