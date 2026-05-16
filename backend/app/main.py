import logging

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.portal import router as portal_router
from app.api.supervisor.dashboard import router as dashboard_router
from app.api.health import router as health_router
from app.api.supervisor.intervention import router as intervention_router
from app.api.webhooks.email import router as email_router
from app.api.webhooks.twilio import router as twilio_router
from app.api.webhooks.whatsapp import router as whatsapp_router
from app.config import get_settings
from app.db import check_database


settings = get_settings()
logging.basicConfig(level=settings.APP_LOG_LEVEL.upper())
logger = logging.getLogger("chris")

app = FastAPI(title="Chris.AI API", version="0.1.0")


@app.on_event("startup")
def on_startup() -> None:
    check_database()
    logger.info("Chris.AI backend booted with settings: %s", settings.safe_boot_summary())


app.include_router(health_router)
app.include_router(auth_router)
app.include_router(portal_router)
app.include_router(whatsapp_router, prefix="/webhooks")
app.include_router(twilio_router, prefix="/webhooks")
app.include_router(email_router, prefix="/webhooks")
app.include_router(dashboard_router, prefix="/supervisor")
app.include_router(intervention_router, prefix="/supervisor")
