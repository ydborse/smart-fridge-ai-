import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User, Alert, NotificationLog, FoodItem, Zone
from app.services.notification import (
    dispatch_telegram,
    format_telegram_alert,
    sanitize_telegram_token
)
from app.services import notification
from app.services.alert_engine import create_spoilage_alert
from datetime import datetime, timedelta


def get_auth_token():
    """Generates a valid JWT token for the demo user."""
    with TestClient(app) as client:
        res = client.post("/api/auth/login", data={"username": "demo@smartfridge.com", "password": "password123"})
        if res.status_code == 200:
            return res.json()["access_token"]
        # Fallback registration
        res = client.post("/api/auth/register", json={
            "email": "demo@smartfridge.com",
            "password": "password123",
            "full_name": "Demo User"
        })
        return res.json().get("access_token")


def test_sanitize_telegram_token():
    """Verifies that sanitize_telegram_token completely strips bot tokens from URLs and text."""
    secret_token = "123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ1234"
    url_with_token = f"https://api.telegram.org/bot{secret_token}/sendMessage"
    
    sanitized = sanitize_telegram_token(url_with_token)
    assert secret_token not in sanitized
    assert "https://api.telegram.org/bot[REDACTED_BOT_TOKEN]/sendMessage" in sanitized

    # Check arbitrary text with token
    text_with_token = f"Error sending to bot token {secret_token} failed with 401"
    assert secret_token not in sanitize_telegram_token(text_with_token)
    assert "[REDACTED_BOT_TOKEN]" in sanitize_telegram_token(text_with_token)


def test_format_telegram_alert():
    """Verifies format_telegram_alert produces clean HTML formatted alerts with emojis and details."""
    html_msg = format_telegram_alert(
        title="Food Spoilage Alert",
        message="Milk is spoiled. Please inspect immediately.",
        food_name="Organic Whole Milk",
        category="Dairy",
        severity="critical",
        alert_type="Food Spoilage Alert",
        days_until_expiry=-1,
        repeat_count=1
    )
    assert "SMART FRIDGE SPOILAGE ALERT" in html_msg
    assert "Organic Whole Milk" in html_msg
    assert "Dairy" in html_msg
    assert "Please inspect and remove" in html_msg


@pytest.mark.asyncio
async def test_telegram_dispatch_success_mock():
    """
    Verifies that dispatch_telegram makes an HTTP POST to the Telegram Bot API
    and returns a success dictionary with provider_message_id and status='delivered'.
    """
    fake_token = "987654321:AAFakeTelegramBotTokenForTestingOnlyXYZ"
    fake_chat_id = "123456789"
    
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "ok": True,
        "result": {
            "message_id": 54321,
            "chat": {"id": int(fake_chat_id), "type": "private"}
        }
    }
    mock_response.raise_for_status = MagicMock()

    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", fake_chat_id), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value = mock_response

        res = await dispatch_telegram(
            chat_id=fake_chat_id,
            message="Test message",
            html_message="<b>Test message</b>"
        )

        assert res["provider"] == "telegram"
        assert res["provider_message_id"] == "54321"
        assert res["status"] == "delivered"
        assert res["simulated"] is False
        assert res["recipient"] == fake_chat_id

        # Verify call arguments
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        payload = call_kwargs["json"]
        assert payload["chat_id"] == fake_chat_id
        assert payload["parse_mode"] == "HTML"
        assert "Test message" in payload["text"]
        
        # Verify token is in call URL but not leaked elsewhere
        called_url = mock_post.call_args[0][0]
        assert f"bot{fake_token}/sendMessage" in called_url


@pytest.mark.asyncio
async def test_telegram_dispatch_failure_api_error_does_not_expose_token():
    """
    Verifies that when Telegram returns an HTTP error (e.g. 401 Unauthorized or 400 Chat Not Found),
    the exception is raised cleanly and the bot token is completely scrubbed from error details.
    """
    fake_token = "987654321:AAFakeTelegramBotTokenForTestingOnlyXYZ"
    fake_chat_id = "123456789"

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 401
    mock_response.json.return_value = {
        "ok": False,
        "error_code": 401,
        "description": "Unauthorized"
    }

    req = httpx.Request("POST", f"https://api.telegram.org/bot{fake_token}/sendMessage")
    http_err = httpx.HTTPStatusError("401 Client Error", request=req, response=mock_response)
    mock_response.raise_for_status.side_effect = http_err

    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", fake_chat_id), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            await dispatch_telegram(chat_id=fake_chat_id, message="Test error")

        err_str = str(exc_info.value)
        # Token must NEVER appear in the exception message
        assert fake_token not in err_str
        assert "Unauthorized" in err_str


@pytest.mark.asyncio
async def test_telegram_dispatch_unconfigured_raises_error():
    """
    Verifies that placeholder or missing credentials raise a descriptive ValueError
    without attempting network calls.
    """
    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", "PASTE_YOUR_BOTFATHER_TOKEN_HERE"), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", "PASTE_YOUR_CHAT_ID_HERE"), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True):
        
        with pytest.raises(ValueError) as exc_info:
            await dispatch_telegram(chat_id=None, message="Test")
        
        assert "TELEGRAM_BOT_TOKEN" in str(exc_info.value)
        assert "PASTE_YOUR" not in str(exc_info.value) or "backend/.env" in str(exc_info.value)


def test_api_settings_test_telegram_endpoint():
    """
    Verifies POST /api/settings/test-telegram endpoint succeeds with mock confirmation
    and never exposes the bot token in JSON response.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    fake_token = "1122334455:AAFakeTokenTestingAPI12345"
    fake_chat = "99887766"

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 778899, "chat": {"id": int(fake_chat)}}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", fake_chat), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value = mock_resp

        with TestClient(app) as client:
            res = client.post(f"/api/settings/test-telegram?chat_id={fake_chat}", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["channel"] == "telegram"
            assert data["provider"] == "telegram"
            assert data["provider_message_id"] == "778899"
            assert data["delivery_status"] == "delivered"
            # Ensure bot token is NEVER exposed anywhere in response
            assert fake_token not in str(data)


def test_api_test_notification_endpoint_dispatches_telegram():
    """
    Verifies POST /api/alerts/test-notification triggers Telegram alert and confirms delivery.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    fake_token = "1122334455:AAFakeTokenTestingAPI12345"
    fake_chat = "99887766"

    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "ok": True,
        "result": {"message_id": 889900, "chat": {"id": int(fake_chat)}}
    }
    mock_resp.raise_for_status = MagicMock()

    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", fake_chat), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
         patch("app.services.notification.settings.TWILIO_ENABLED", False), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        
        mock_post.return_value = mock_resp

        with TestClient(app) as client:
            res = client.post("/api/alerts/test-notification?channel=all", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert "Telegram: Delivered to chat" in data["summary"]
            assert "889900" in data["summary"]

            # Verify results payload
            assert "telegram" in data["results"]
            tg_res = data["results"]["telegram"]
            assert tg_res["success"] is True
            assert tg_res["status"] == "delivered"
            assert tg_res["provider"] == "telegram"
            assert tg_res["provider_message_id"] == "889900"
            assert fake_token not in str(data)


@pytest.mark.asyncio
async def test_food_spoilage_alert_workflow_dispatches_telegram():
    """
    Verifies that when a spoilage alert is triggered, notification.send dispatches to Telegram,
    records a NotificationLog with channel='telegram', provider='telegram', and status='delivered'.
    """
    db = SessionLocal()
    orig_chat_id = None
    orig_pref = None
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        orig_chat_id = user.telegram_chat_id
        orig_pref = user.telegram_notifications_enabled
        user.telegram_notifications_enabled = True
        user.telegram_chat_id = "554433221"
        db.commit()

        zone = db.query(Zone).first()
        food = FoodItem(
            user_id=user.id,
            name="Fresh Cream",
            category="Dairy",
            item_type="dairy",
            zone_id=zone.id if zone else None,
            quantity=1.0,
            unit="box",
            added_at=datetime.utcnow(),
            expiry_date=datetime.utcnow() - timedelta(days=1),
            freshness_status="Rotten",
            is_used=False,
            is_discarded=False
        )
        db.add(food)
        db.commit()
        db.refresh(food)

        fake_token = "7788990011:AAFakeTokenDairyWorkflow12345"
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "ok": True,
            "result": {"message_id": 445566, "chat": {"id": 554433221}}
        }
        mock_resp.raise_for_status = MagicMock()

        with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
             patch("app.services.notification.settings.TELEGRAM_CHAT_ID", "554433221"), \
             patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
             patch("app.services.notification.settings.TWILIO_ENABLED", False), \
             patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            
            mock_post.return_value = mock_resp

            alert, created = await create_spoilage_alert(
                db=db,
                user=user,
                food=food,
                confidence=0.98
            )

            assert created is True
            assert alert is not None
            mock_post.assert_called_once()

            # Verify NotificationLog
            log = db.query(NotificationLog).filter(
                NotificationLog.alert_id == alert.id,
                NotificationLog.channel == "telegram"
            ).first()
            assert log is not None
            assert log.provider == "telegram"
            assert log.provider_message_id == "445566"
            assert log.status == "delivered"
            assert fake_token not in log.error_message if log.error_message else True

        # Clean up
        db.delete(food)
        db.delete(alert)
        if log:
            db.delete(log)
        db.commit()
    finally:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        if user:
            user.telegram_chat_id = orig_chat_id
            if orig_pref is not None:
                user.telegram_notifications_enabled = orig_pref
            db.commit()
        db.close()


@pytest.mark.asyncio
async def test_get_telegram_diagnostic_safe_and_masked():
    """
    Verifies that get_telegram_diagnostic returns masked information and never exposes secrets.
    """
    from app.services.notification import get_telegram_diagnostic

    fake_token = "123456789:AABBCCTestSecretTokenDoNotExpose12345"
    fake_chat = "9876543210"

    mock_me = MagicMock(spec=httpx.Response)
    mock_me.status_code = 200
    mock_me.headers = {"content-type": "application/json"}
    mock_me.json.return_value = {
        "ok": True,
        "result": {
            "id": 123456789,
            "is_bot": True,
            "first_name": "Test Bot",
            "username": "TestFridgeBot"
        }
    }

    mock_chat = MagicMock(spec=httpx.Response)
    mock_chat.status_code = 200
    mock_chat.headers = {"content-type": "application/json"}
    mock_chat.json.return_value = {
        "ok": True,
        "result": {
            "id": 9876543210,
            "first_name": "Test User",
            "type": "private"
        }
    }

    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", fake_chat), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:

        mock_get.return_value = mock_me
        mock_post.return_value = mock_chat

        diag = await get_telegram_diagnostic()
        assert diag["status"] == "verified"
        assert diag["token_present"] is True
        assert diag["chat_id_present"] is True
        assert diag["api_reachable"] is True
        # Verify secret token is NOT in diagnostic output
        assert fake_token not in str(diag)
        # Verify masked format
        assert "..." in diag["token_masked"]
        assert "***" in diag["chat_id_masked"]


def test_api_telegram_diagnostic_endpoint():
    """
    Verifies GET /api/settings/telegram-diagnostic endpoint returns safe diagnostic.
    """
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    fake_token = "123456789:AABBCCTestSecretTokenDoNotExpose12345"
    fake_chat = "9876543210"

    mock_me = MagicMock(spec=httpx.Response)
    mock_me.status_code = 200
    mock_me.headers = {"content-type": "application/json"}
    mock_me.json.return_value = {
        "ok": True,
        "result": {"id": 123456789, "is_bot": True, "first_name": "Test Bot", "username": "TestFridgeBot"}
    }

    mock_chat = MagicMock(spec=httpx.Response)
    mock_chat.status_code = 200
    mock_chat.headers = {"content-type": "application/json"}
    mock_chat.json.return_value = {
        "ok": True,
        "result": {"id": 9876543210, "first_name": "Test User", "type": "private"}
    }

    with patch("app.services.notification.settings.TELEGRAM_BOT_TOKEN", fake_token), \
         patch("app.services.notification.settings.TELEGRAM_CHAT_ID", fake_chat), \
         patch("app.services.notification.settings.TELEGRAM_ENABLED", True), \
         patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get, \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:

        mock_get.return_value = mock_me
        mock_post.return_value = mock_chat

        with TestClient(app) as client:
            res = client.get("/api/settings/telegram-diagnostic", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "verified"
            assert data["token_present"] is True
            assert fake_token not in str(data)

