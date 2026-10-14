from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_ready_reports_sending_disabled_by_default():
    body = client.get("/ready").json()
    assert body["kb_loaded"] is True
    assert body["whatsapp_sending_enabled"] is False
