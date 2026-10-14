from fastapi import FastAPI

from app.config import get_settings
from app.infrastructure.kb import load_kb

VERSION = "0.1.0"
app = FastAPI(title="Kira Sales Agent", version=VERSION)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": get_settings().app_name, "version": VERSION}


@app.get("/ready")
def ready() -> dict[str, object]:
    kb = load_kb()
    return {
        "status": "ok",
        "kb_loaded": bool(kb.get("templates")),
        "whatsapp_sending_enabled": get_settings().whatsapp_sending_enabled,
    }
