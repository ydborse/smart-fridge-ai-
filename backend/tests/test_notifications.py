import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, NotificationLog
from app.services import notification
from app.services.notification import (
    render_alert_email_html,
    render_daily_digest_html,
    send_with_retries
)

@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
    if not user:
        from app.seed import seed_database
        seed_database()
    db.close()

def test_html_email_template_rendering():
    metadata = {
        "food_name": "Organic Whole Milk",
        "expiry_date": "Oct 05, 2026",
        "status": "Expiring Soon",
        "food_item_id": 42
    }
    html = render_alert_email_html(
        title="Milk Expiring Soon",
        message="Please use within 2 days.",
        metadata=metadata
    )
    assert "Organic Whole Milk" in html
    assert "Oct 05, 2026" in html
    assert "Expiring Soon" in html
    assert "Mark as Used / Consumed" in html
    assert "action=mark_used&amp;id=42" in html or "action=mark_used&id=42" in html

def test_daily_digest_html_rendering():
    items = [
        {"id": 1, "name": "Greek Yogurt", "zone": "Top Shelf", "days_left": 1},
        {"id": 2, "name": "Strawberries", "zone": "Fruit Drawer", "days_left": 2}
    ]
    html = render_daily_digest_html(items)
    assert "Greek Yogurt" in html
    assert "Strawberries" in html
    assert "Top Shelf" in html
    assert "1 day(s) left" in html

@pytest.mark.asyncio
async def test_retry_mechanism():
    call_count = 0
    async def failing_delivery():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("Temporary timeout")
        return "mock_provider"

    success, provider, err, attempts = await send_with_retries(failing_delivery, max_retries=3)
    assert success is True
    assert provider == "mock_provider"
    assert attempts == 3

def test_notification_endpoints():
    with TestClient(app) as client:
        # 1. Login to get token
        login_res = client.post("/api/auth/login", json={
            "email": "demo@smartfridge.com",
            "password": "SmartFridge123!"
        })
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Get VAPID public key
        vapid_res = client.get("/api/settings/vapid-public-key", headers=headers)
        assert vapid_res.status_code == 200
        data = vapid_res.json()
        assert "public_key" in data
        assert len(data["public_key"]) > 20

        # 3. Register Web Push subscription
        sub_payload = {
            "endpoint": "https://fcm.googleapis.com/fcm/send/sample-token",
            "keys": {
                "p256dh": "BNcRdreALRFXTkOOUHK1EtK2wtaz5Ry4YfYCA_0QT9t0A37TIJa07zB85Oc2",
                "auth": "tBHItJI5svbpez7KI4CCXg"
            }
        }
        sub_res = client.post("/api/settings/subscribe-push", json=sub_payload, headers=headers)
        assert sub_res.status_code == 200
        assert sub_res.json()["status"] == "subscribed"

        # 4. Get notification logs
        logs_res = client.get("/api/settings/notifications-log", headers=headers)
        assert logs_res.status_code == 200
        logs = logs_res.json()
        assert isinstance(logs, list)
        assert len(logs) >= 1
        assert "channel" in logs[0]
        assert "status" in logs[0]

        # 5. Test Email endpoint
        email_res = client.post("/api/settings/test-email", headers=headers)
        assert email_res.status_code == 200
        assert email_res.json()["status"] == "success"

        # 6. Test SMS endpoint (mocked Twilio)
        from unittest.mock import MagicMock
        mock_msg = MagicMock()
        mock_msg.sid = "SMtest_notif_12345"
        mock_msg.status = "queued"
        mock_msg.error_code = None
        mock_msg.error_message = None
        mock_client = MagicMock()
        mock_client.messages.create.return_value = mock_msg

        with patch("app.services.notification.settings.TWILIO_ENABLED", True), \
             patch("app.services.notification.settings.TWILIO_ACCOUNT_SID", "ACtest1234567890abcdef1234567890"), \
             patch("app.services.notification.settings.TWILIO_AUTH_TOKEN", "authtest1234567890abcdef"), \
             patch("app.services.notification.settings.TWILIO_FROM_NUMBER", "+15005550006"), \
             patch("app.services.notification.Client", return_value=mock_client):
            sms_res = client.post("/api/settings/test-sms", headers=headers)
            assert sms_res.status_code == 200
            assert sms_res.json()["status"] == "success"
            assert sms_res.json()["provider_message_id"] == "SMtest_notif_12345"
