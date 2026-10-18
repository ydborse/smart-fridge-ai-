import platform
if hasattr(platform, "_wmi_query"):
    platform._wmi_query = lambda table, *args: ("10.0.22631", 1, "Multiprocessor Free", 0, 0)

import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, Base, get_db
from app.seed import seed_database
from app.services.scheduler import start_scheduler, shutdown_scheduler

# Routers
from app.routers import (
    auth, foods, predict, barcode, ocr,
    zones, sensors, alerts, audit, dashboard,
    history, settings as settings_router, dataset
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure tables, migrations, and seed data exist
    logger.info("Initializing Smart Fridge Backend...")
    Base.metadata.create_all(bind=engine)
    try:
        from app.migrations import run_migrations
        run_migrations()
    except Exception as e:
        logger.warning(f"Schema migration warning: {e}")
    try:
        seed_database()
    except Exception as e:
        logger.warning(f"Seed database warning: {e}")

    # Validate SMS configuration during startup
    if settings.SMS_ENABLED:
        has_twilio = bool(
            settings.TWILIO_ACCOUNT_SID and
            settings.TWILIO_AUTH_TOKEN and
            (settings.TWILIO_FROM_NUMBER or settings.TWILIO_MESSAGING_SERVICE_SID) and
            settings.TWILIO_ACCOUNT_SID.startswith("AC") and
            "your_twilio" not in settings.TWILIO_AUTH_TOKEN
        )
        if has_twilio:
            from app.services.notification import normalize_phone_number
            norm_to = normalize_phone_number(settings.SMS_TO_NUMBER or "")
            logger.info(f"SMS Alert Service: ACTIVE (Twilio from: {settings.TWILIO_FROM_NUMBER or settings.TWILIO_MESSAGING_SERVICE_SID}, to: {norm_to}, interval: {getattr(settings, 'SMS_REMINDER_INTERVAL_MINUTES', 120)}m)")
        else:
            logger.warning("SMS Alert Service: SMS_ENABLED=true but Twilio credentials are missing or unconfigured in .env. Live carrier SMS will not be sent until configured.")
    else:
        logger.info(f"SMS Alert Service: DISABLED (SMS_ENABLED=false). Operating in simulation mode with target recipient: {settings.SMS_TO_NUMBER or 'None'}")

    # Start APScheduler for sensors and alert rules
    start_scheduler()
    yield
    # Shutdown
    shutdown_scheduler()
    logger.info("Smart Fridge Backend shut down cleanly.")

app = FastAPI(
    title="Smart Fridge Assistant API",
    description="Backend API for Smart Refrigerator Food Management, Freshness AI, Barcode Scanner & Digital Twin",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded media and images
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
app.mount("/storage", StaticFiles(directory=settings.STORAGE_DIR), name="storage")

# Include Routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(foods.router, prefix=settings.API_V1_STR)
app.include_router(predict.router, prefix=settings.API_V1_STR)
app.include_router(barcode.router, prefix=settings.API_V1_STR)
app.include_router(ocr.router, prefix=settings.API_V1_STR)
app.include_router(zones.router, prefix=settings.API_V1_STR)
app.include_router(sensors.router, prefix=settings.API_V1_STR)
app.include_router(alerts.router, prefix=settings.API_V1_STR)
app.include_router(audit.router, prefix=settings.API_V1_STR)
app.include_router(dashboard.router, prefix=settings.API_V1_STR)
app.include_router(history.router, prefix=settings.API_V1_STR)
app.include_router(settings_router.router, prefix=settings.API_V1_STR)
app.include_router(dataset.router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "app": settings.PROJECT_NAME,
        "status": "online",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/health")
@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db_ok = False
    try:
        from app.models import Zone
        _ = db.query(Zone).count()
        db_ok = True
    except Exception:
        db_ok = False

    models_status = {
        "food_classifier": False,
        "freshness_classifier": False,
        "dairy_classifier": False
    }

    try:
        from app.services.ml_inference import ml_service
        models_status["food_classifier"] = ml_service.food_model is not None
        models_status["freshness_classifier"] = ml_service.freshness_model is not None
    except Exception:
        pass

    try:
        from app.services.dairy_classifier import dairy_service
        models_status["dairy_classifier"] = dairy_service.model is not None
    except Exception:
        pass

    from app.services.scheduler import scheduler
    scheduler_info = {
        "running": scheduler.running,
        "jobs": [j.id for j in scheduler.get_jobs()] if scheduler.running else []
    }

    all_ready = db_ok and all(models_status.values())
    return {
        "status": "healthy" if all_ready else "degraded",
        "service": "smart-fridge-api",
        "database": "connected" if db_ok else "disconnected",
        "models": models_status,
        "scheduler": scheduler_info
    }

