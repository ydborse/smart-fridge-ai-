import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, Alert, FoodItem, Zone, NotificationLog
from app.services.notification import (
    normalize_phone_number,
    is_dairy_item,
    format_sms_alert,
    dispatch_sms,
    send
)
from app.services.alert_engine import (
    should_trigger_sms_for_alert,
    resolve_alert,
    resolve_alerts_for_food
)
from app.services.scheduler import job_process_repeating_alerts


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
    if not user:
        from app.seed import seed_database
        seed_database()
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    # Ensure test user has SMS enabled and a phone number configured
    user.phone_number = "+919876543210"
    user.sms_enabled = True
    user.sms_for_dairy = True
    user.sms_for_expired = True
    user.sms_for_expiring = True
    user.sms_for_temperature = True
    user.sms_repeat_interval_minutes = 15
    user.sms_max_duration_minutes = 120
    db.commit()
    db.close()


def get_auth_token():
    with TestClient(app) as client:
        res = client.post("/api/auth/login", json={
            "email": "demo@smartfridge.com",
            "password": "SmartFridge123!"
        })
        assert res.status_code == 200
        return res.json()["access_token"]


# =====================================================================
# 1. Phone Normalization & Message Formatting Tests
# =====================================================================

def test_normalize_phone_number_india_and_e164():
    # 10-digit Indian numbers
    assert normalize_phone_number("9876543210") == "+919876543210"
    # Leading 0 Indian numbers
    assert normalize_phone_number("09876543210") == "+919876543210"
    # Number with spaces and dashes
    assert normalize_phone_number("+91 98765-43210") == "+919876543210"
    # US number
    assert normalize_phone_number("+1 (415) 555-2671") == "+14155552671"
    # Empty or None
    assert normalize_phone_number("") == ""
    assert normalize_phone_number(None) == ""


def test_is_dairy_item_detection():
    assert is_dairy_item("Organic Whole Milk") is True
    assert is_dairy_item("Greek Yogurt Strawberry") is True
    assert is_dairy_item("Fresh Paneer 200g") is True
    assert is_dairy_item("Cheddar Cheese Slices") is True
    assert is_dairy_item("Fresh Curd") is True
    assert is_dairy_item("Amul Dahi") is True
    assert is_dairy_item("Apples") is False
    assert is_dairy_item("Raw Chicken Breast") is False
    assert is_dairy_item(None) is False


def test_format_sms_alert_length_and_content():
    # Expired dairy
    msg_expired = format_sms_alert(
        title="Milk Expired",
        message="Expired 1 day ago.",
        alert_type="Expired / Remove Now",
        food_name="Whole Milk"
    )
    assert "whole milk has expired" in msg_expired.lower()
    assert len(msg_expired) <= 160

    # Temperature alert
    msg_temp = format_sms_alert(
        title="High Temperature",
        message="Temp is 9.5C",
        alert_type="Temperature Warning",
        temp_c=9.5
    )
    assert "refrigerator temperature is above the safe configured limit" in msg_temp.lower()
    assert len(msg_temp) <= 160

    # Expiring soon dairy
    msg_expiring = format_sms_alert(
        title="Paneer Expiring Soon",
        message="Expires in 1 day",
        alert_type="Expiring Soon",
        food_name="Paneer"
    )
    assert "paneer is nearing its expiry date" in msg_expiring.lower()
    assert len(msg_expiring) <= 160


# =====================================================================
# 2. Twilio Mocking & Error Handling Tests
# =====================================================================

@pytest.mark.asyncio
async def test_dispatch_sms_disabled_or_missing_credentials_fails():
    with patch("app.services.notification.settings.TWILIO_ENABLED", False):
        with pytest.raises(ValueError) as exc:
            await dispatch_sms("+919876543210", "SMART FRIDGE ALERT: Test alert")
        assert "Twilio SMS is disabled" in str(exc.value)

    with patch("app.services.notification.settings.TWILIO_ENABLED", True), \
         patch("app.services.notification.settings.TWILIO_ACCOUNT_SID", ""), \
         patch("app.services.notification.settings.TWILIO_AUTH_TOKEN", ""):
        with pytest.raises(ValueError) as exc:
            await dispatch_sms("+919876543210", "SMART FRIDGE ALERT: Test alert")
        assert "Twilio credentials not configured" in str(exc.value)


@pytest.mark.asyncio
async def test_dispatch_sms_real_twilio_success_mock():
    mock_msg = MagicMock()
    mock_msg.sid = "SMabcdef1234567890abcdef1234567890"
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
        res = await dispatch_sms("+919876543210", "SMART FRIDGE ALERT: Test real mock")
        assert res["provider"] == "twilio"
        assert res["provider_message_id"] == "SMabcdef1234567890abcdef1234567890"
        assert res["status"] == "queued"
        assert res["simulated"] is False
        mock_client.messages.create.assert_called_once()
        call_kwargs = mock_client.messages.create.call_args[1]
        assert call_kwargs["to"] == "+919876543210"
        assert call_kwargs["from_"] == "+15005550006"
        assert "SMART FRIDGE ALERT: Test real mock" in call_kwargs["body"]


@pytest.mark.asyncio
async def test_dispatch_sms_twilio_exception_handled():
    mock_client = MagicMock()
    mock_client.messages.create.side_effect = Exception("Twilio error [20003]: Authentication Error")

    with patch("app.services.notification.settings.TWILIO_ENABLED", True), \
         patch("app.services.notification.settings.TWILIO_ACCOUNT_SID", "ACinvalid1234567890abcdef1234567890"), \
         patch("app.services.notification.settings.TWILIO_AUTH_TOKEN", "invalidtoken1234567890abcdef"), \
         patch("app.services.notification.settings.TWILIO_FROM_NUMBER", "+15005550006"), \
         patch("app.services.notification.Client", return_value=mock_client):
        with pytest.raises(Exception) as exc_info:
            await dispatch_sms("+919876543210", "SMART FRIDGE ALERT: Test error")
        assert "Twilio error" in str(exc_info.value)


# =====================================================================
# 3. Alert Filtering & Immediate SMS Trigger Tests
# =====================================================================

def test_should_trigger_sms_for_alert_rules():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    # Dairy expired -> Should trigger
    assert should_trigger_sms_for_alert(user, "Expired / Remove Now", "critical", "Milk", None) is True

    # Dairy expiring soon -> Should trigger
    assert should_trigger_sms_for_alert(user, "Expiring Soon", "warning", "Paneer", None) is True

    # Temperature critical -> Should trigger
    assert should_trigger_sms_for_alert(user, "Temperature Warning", "critical", None, 10.0) is True

    # Non-dairy fruit expiring soon with warning severity -> Does not spam SMS
    assert should_trigger_sms_for_alert(user, "Expiring Soon", "warning", "Apples", None) is False

    # Disabled user SMS -> Never triggers
    user.sms_enabled = False
    assert should_trigger_sms_for_alert(user, "Expired / Remove Now", "critical", "Milk", None) is False
    user.sms_enabled = True
    db.close()


# =====================================================================
# 4. Repeat Notification Scheduler & 2-Hour Cutoff Tests
# =====================================================================

@pytest.mark.asyncio
async def test_scheduler_repeats_active_alert_within_window():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    now = datetime.utcnow()
    # Create an alert created 30 mins ago, first SMS sent 30 mins ago, next due now
    alert = Alert(
        user_id=user.id,
        alert_type="Expired / Remove Now",
        severity="critical",
        title="Test Yogurt Expired",
        message="SMART FRIDGE ALERT: Your yogurt has expired.",
        is_read=False,
        is_resolved=False,
        first_sms_sent_at=now - timedelta(minutes=30),
        last_sms_sent_at=now - timedelta(minutes=30),
        next_sms_scheduled_at=now - timedelta(minutes=1),
        sms_repeat_count=1,
        channel_sent="sms"
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    # Run repeat job
    with patch("app.services.notification.dispatch_sms") as mock_dispatch:
        mock_dispatch.return_value = {
            "provider": "twilio_mock",
            "provider_message_id": "SM_REPEAT_TEST",
            "status": "sent",
            "is_simulated": False
        }
        await job_process_repeating_alerts()

    # Verify alert state
    db = SessionLocal()
    refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
    assert refreshed.sms_repeat_count == 2
    assert refreshed.next_sms_scheduled_at is not None
    # Next schedule should be ~15 mins from now
    assert refreshed.next_sms_scheduled_at > datetime.utcnow()

    # Cleanup
    db.delete(refreshed)
    db.commit()
    db.close()


@pytest.mark.asyncio
async def test_scheduler_enforces_two_hour_max_duration_cutoff():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    now = datetime.utcnow()
    # Alert first sent 121 minutes ago (exceeding 2h duration)
    alert = Alert(
        user_id=user.id,
        alert_type="Expired / Remove Now",
        severity="critical",
        title="2 Hour Limit Alert",
        message="SMART FRIDGE ALERT: Your milk has expired.",
        is_read=False,
        is_resolved=False,
        first_sms_sent_at=now - timedelta(minutes=121),
        last_sms_sent_at=now - timedelta(minutes=15),
        next_sms_scheduled_at=now - timedelta(minutes=1),
        sms_repeat_count=8,
        channel_sent="sms"
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    with patch("app.services.notification.dispatch_sms") as mock_dispatch:
        await job_process_repeating_alerts()
        # Should NOT dispatch any message because 2 hours elapsed
        mock_dispatch.assert_not_called()

    # Verify that next_sms_scheduled_at was cancelled/cleared
    db = SessionLocal()
    refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
    assert refreshed.next_sms_scheduled_at is None
    assert refreshed.sms_repeat_count == 8

    db.delete(refreshed)
    db.commit()
    db.close()


@pytest.mark.asyncio
async def test_scheduler_persists_schedule_across_restarts():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    now = datetime.utcnow()
    # Created 105 minutes ago (1 hour 45 minutes into 2-hour window)
    alert = Alert(
        user_id=user.id,
        alert_type="Expired / Remove Now",
        severity="critical",
        title="Restart Persistence Alert",
        message="SMART FRIDGE ALERT: Cold chain broken.",
        is_read=False,
        is_resolved=False,
        first_sms_sent_at=now - timedelta(minutes=105),
        last_sms_sent_at=now - timedelta(minutes=20),
        next_sms_scheduled_at=now - timedelta(minutes=1),
        sms_repeat_count=7,
        channel_sent="sms"
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    with patch("app.services.notification.dispatch_sms") as mock_dispatch:
        mock_dispatch.return_value = {
            "provider": "twilio_mock",
            "provider_message_id": "SM_RESTART_TEST",
            "status": "sent",
            "is_simulated": False
        }
        await job_process_repeating_alerts()
        # Sent repeat #8
        assert mock_dispatch.call_count == 1

    db = SessionLocal()
    refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
    assert refreshed.sms_repeat_count == 8
    # Since 105 min + 15 min = 120 min, next interval (120 min) reaches cutoff, so no further repeats!
    assert refreshed.next_sms_scheduled_at is None

    db.delete(refreshed)
    db.commit()
    db.close()


# =====================================================================
# 5. Alert Resolution & Silence Repeating SMS Tests
# =====================================================================

def test_resolve_alert_cancels_repeats():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    now = datetime.utcnow()
    alert = Alert(
        user_id=user.id,
        alert_type="Expired / Remove Now",
        severity="critical",
        title="Alert to Resolve",
        message="Test alert",
        is_read=False,
        is_resolved=False,
        first_sms_sent_at=now - timedelta(minutes=10),
        next_sms_scheduled_at=now + timedelta(minutes=5),
        sms_repeat_count=1
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id

    # Call resolve_alert service
    resolved = resolve_alert(db, alert_id, user.id)
    assert resolved is not None
    assert resolved.is_resolved is True

    refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
    assert refreshed.is_resolved is True
    assert refreshed.is_read is True
    assert refreshed.resolved_at is not None
    assert refreshed.next_sms_scheduled_at is None

    db.delete(refreshed)
    db.commit()
    db.close()


def test_resolve_alerts_when_food_consumed_or_discarded():
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
    zone = db.query(Zone).first()

    food = FoodItem(
        user_id=user.id,
        zone_id=zone.id,
        name="Test Milk Carton",
        category="Dairy",
        item_type="packaged",
        expiry_date=datetime.utcnow() - timedelta(days=1),
        freshness_status="Expired"
    )
    db.add(food)
    db.commit()

    alert = Alert(
        user_id=user.id,
        food_item_id=food.id,
        alert_type="Expired / Remove Now",
        severity="critical",
        title="Food Item Alert",
        message="Food expired",
        is_resolved=False,
        next_sms_scheduled_at=datetime.utcnow() + timedelta(minutes=15),
        sms_repeat_count=1
    )
    db.add(alert)
    db.commit()

    count = resolve_alerts_for_food(db, food.id)
    assert count >= 1

    refreshed_alert = db.query(Alert).filter(Alert.id == alert.id).first()
    assert refreshed_alert.is_resolved is True
    assert refreshed_alert.next_sms_scheduled_at is None

    db.delete(alert)
    db.delete(food)
    db.commit()
    db.close()


# =====================================================================
# 6. REST API Endpoints: Resolve, Settings, and Test SMS
# =====================================================================

def test_api_resolve_alert_endpoint():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
    alert = Alert(
        user_id=user.id,
        alert_type="Expired / Remove Now",
        severity="critical",
        title="API Resolve Test",
        message="Test message",
        is_resolved=False,
        next_sms_scheduled_at=datetime.utcnow() + timedelta(minutes=10)
    )
    db.add(alert)
    db.commit()
    alert_id = alert.id
    db.close()

    with TestClient(app) as client:
        res = client.put(f"/api/alerts/{alert_id}/resolve", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["is_resolved"] is True
        assert data["next_sms_scheduled_at"] is None

    db = SessionLocal()
    refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
    db.delete(refreshed)
    db.commit()
    db.close()


def test_api_update_sms_settings_endpoint():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app) as client:
        # Update settings
        update_payload = {
            "sms_enabled": True,
            "phone_number": "9876543210", # Raw Indian number -> will normalize to +91
            "sms_repeat_interval_minutes": 20,
            "sms_max_duration_minutes": 90,
            "sms_for_dairy": True,
            "sms_for_expired": True
        }
        res = client.put("/api/settings", json=update_payload, headers=headers)
        assert res.status_code == 200
        user_data = res.json()
        assert user_data["phone_number"] == "+919876543210"
        assert user_data["sms_repeat_interval_minutes"] == 20
        assert user_data["sms_max_duration_minutes"] == 90

        # Verify get settings returns the updated status
        get_res = client.get("/api/settings", headers=headers)
        assert get_res.status_code == 200
        settings_data = get_res.json()
        assert settings_data["sms_system_status"]["configured"] in (True, False)
        assert settings_data["user"]["phone_number"] == "+919876543210"


def test_api_send_test_sms_endpoint():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    mock_msg = MagicMock()
    mock_msg.sid = "SMtest_api_sid_1234567890"
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
        with TestClient(app) as client:
            res = client.post("/api/settings/test-sms", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert data["provider_message_id"] == "SMtest_api_sid_1234567890"
            assert data["delivery_status"] in ("queued", "accepted", "sent")
            assert data["is_simulated"] is False
            assert "SMART FRIDGE" in data["message"]


def test_api_send_test_sms_fails_when_unconfigured():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    with patch("app.services.notification.settings.TWILIO_ENABLED", False):
        with TestClient(app) as client:
            res = client.post("/api/settings/test-sms", headers=headers)
            assert res.status_code == 502
            assert "Twilio SMS is disabled" in res.json()["detail"]


def test_api_test_notification_endpoint_with_twilio():
    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}

    mock_msg = MagicMock()
    mock_msg.sid = "SMtest_alert_sid_9999"
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
        with TestClient(app) as client:
            res = client.post("/api/alerts/test-notification?channel=sms", headers=headers)
            assert res.status_code == 200
            data = res.json()
            assert data["status"] == "success"
            assert "SMtest_alert_sid_9999" in data["summary"]
            sms_res = data["results"]["sms"]
            assert sms_res["success"] is True
            assert sms_res["provider_message_id"] == "SMtest_alert_sid_9999"
            assert sms_res["status"] == "accepted"


@pytest.mark.asyncio
async def test_produce_spoilage_alert_triggers_real_twilio_sms():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        from app.models import Zone
        zone = db.query(Zone).first()
        food = FoodItem(
            user_id=user.id,
            name="Rotten Tomato",
            category="Vegetables",
            item_type="vegetable",
            zone_id=zone.id,
            quantity=2.0,
            unit="pcs",
            added_at=datetime.utcnow(),
            expiry_date=datetime.utcnow() - timedelta(days=2),
            freshness_status="Rotten",
            is_used=False,
            is_discarded=False
        )
        db.add(food)
        db.commit()
        db.refresh(food)

        mock_msg = MagicMock()
        mock_msg.sid = "SMspoilage_tomato_sid_123"
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
            from app.services.alert_engine import create_spoilage_alert
            alert, created = await create_spoilage_alert(
                db=db,
                user=user,
                food=food,
                confidence=0.96
            )

            assert created is True
            assert alert is not None
            mock_client.messages.create.assert_called_once()
            call_kwargs = mock_client.messages.create.call_args[1]
            assert "Tomato" in call_kwargs["body"] or "tomato" in call_kwargs["body"]
            assert "inspect and remove" in call_kwargs["body"].lower()

            log = db.query(NotificationLog).filter(
                NotificationLog.alert_id == alert.id,
                NotificationLog.channel == "sms"
            ).first()
            assert log is not None
            assert log.provider == "twilio"
            assert log.provider_message_id == "SMspoilage_tomato_sid_123"
            assert log.status == "accepted"

            db.delete(log)
            db.delete(alert)
            db.delete(food)
            db.commit()
    finally:
        db.close()
