import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient

from app.main import app
from app.database import Base, engine, SessionLocal
from app.models import User, Alert, FoodItem, Zone, NotificationLog
from app.services.alert_engine import (
    create_spoilage_alert,
    resolve_alert,
    resolve_alerts_for_food
)
from app.services.scheduler import job_process_repeating_alerts
from app.services import notification


@pytest.fixture(scope="module", autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
    if not user:
        from app.seed import seed_database
        seed_database()
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()

    # Ensure user has spoilage reminders and push enabled
    user.spoilage_reminder_enabled = True
    user.spoilage_reminder_interval_minutes = 120
    user.push_for_spoilage = True
    user.push_notifications_enabled = True
    user.push_subscription = json.dumps({
        "endpoint": "https://fcm.googleapis.com/fcm/send/fake-test-subscription",
        "keys": {"p256dh": "dummy-p256dh-key", "auth": "dummy-auth-key"}
    })
    db.commit()
    db.close()


def get_auth_token():
    with TestClient(app) as client:
        res = client.post("/api/auth/login", json={
            "email": "demo@smartfridge.com",
            "password": "SmartFridge123!"
        })
        assert res.status_code == 200, f"Login failed: {res.text}"
        return res.json()["access_token"]


def get_or_create_zone(db, code="TEST_ZONE"):
    zone = db.query(Zone).filter(Zone.code == code).first()
    if not zone:
        zone = Zone(
            name="Test Zone",
            code=code,
            target_temp_min=2.0,
            target_temp_max=5.0,
            target_humidity_min=60.0,
            target_humidity_max=80.0,
            current_temp=3.5,
            current_humidity=70.0,
            health_score=95,
            status="normal",
            description="Test zone"
        )
        db.add(zone)
        db.commit()
        db.refresh(zone)
    return zone


def create_test_food(db, user_id, name="Test Apple", freshness="Rotten", expiry_days=None):
    zone = get_or_create_zone(db)
    exp = datetime.utcnow() + timedelta(days=expiry_days) if expiry_days is not None else datetime.utcnow() - timedelta(days=1)
    food = FoodItem(
        user_id=user_id,
        name=name,
        category="Fruits",
        item_type="fruit",
        zone_id=zone.id,
        quantity=1.0,
        unit="pcs",
        added_at=datetime.utcnow(),
        expiry_date=exp,
        freshness_status=freshness,
        is_used=False,
        is_discarded=False,
        estimated_cost=2.5,
        source="fruit_scan"
    )
    db.add(food)
    db.commit()
    db.refresh(food)
    return food


# =========================================================================
# 1. Immediate Alert Creation & Field Verification
# =========================================================================
@pytest.mark.asyncio
async def test_immediate_spoilage_alert_creation_and_fields():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        food = create_test_food(db, user.id, name="Spoiled Honeycrisp Apple", freshness="Rotten")

        with patch("app.services.alert_engine.send_notification", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"web_push": {"success": True}}

            alert, created = await create_spoilage_alert(
                db=db,
                user=user,
                food=food,
                confidence=0.985
            )

            assert created is True
            assert alert is not None
            assert alert.alert_type == "Food Spoilage Alert"
            assert alert.status == "ACTIVE"
            assert alert.is_resolved is False
            assert alert.food_item_id == food.id
            assert alert.confidence_score == 0.985
            assert "🚨 Food Spoilage Alert!" in alert.title
            assert "Spoiled Honeycrisp Apple" in alert.message
            assert alert.last_notification_at is not None
            assert alert.next_reminder_at is not None
            assert alert.reminder_count >= 1

            # Verify next reminder is scheduled ~120 minutes out
            expected_next = alert.last_notification_at + timedelta(minutes=120)
            diff_seconds = abs((alert.next_reminder_at - expected_next).total_seconds())
            assert diff_seconds < 10

            # Verify initial notification was dispatched with deep link to /alerts
            mock_send.assert_called_once()
            call_kwargs = mock_send.call_args[1]
            assert "🚨 Food Spoilage Alert!" in call_kwargs["title"]
            assert call_kwargs["metadata"]["action_url"] == f"/alerts?id={alert.id}"
            assert call_kwargs["metadata"]["food_item_id"] == food.id
    finally:
        db.close()


# =========================================================================
# 2. Idempotency & Duplicate Prevention
# =========================================================================
@pytest.mark.asyncio
async def test_idempotency_and_duplicate_prevention():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        food = create_test_food(db, user.id, name="Idempotent Rotten Banana", freshness="Rotten")

        with patch("app.services.alert_engine.send_notification", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"web_push": {"success": True}}

            alert1, created1 = await create_spoilage_alert(db=db, user=user, food=food)
            assert created1 is True
            first_next_reminder = alert1.next_reminder_at

            # Second request for same item must NOT create a second alert
            alert2, created2 = await create_spoilage_alert(db=db, user=user, food=food)
            assert created2 is False

            assert alert1.id == alert2.id
            assert alert2.next_reminder_at == first_next_reminder

            # Only one active alert in database for this food item
            active_count = db.query(Alert).filter(
                Alert.food_item_id == food.id,
                Alert.status == "ACTIVE"
            ).count()
            assert active_count == 1

            # mock_send should only be called once, not twice
            assert mock_send.call_count == 1
    finally:
        db.close()


# =========================================================================
# 3. 2-Hour Recurring Reminder Execution (Simulated Short Interval)
# =========================================================================
@pytest.mark.asyncio
async def test_2_hour_reminder_scheduler_execution():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        food = create_test_food(db, user.id, name="Scheduler Test Spinach", freshness="Rotten")

        with patch("app.services.alert_engine.send_notification", new_callable=AsyncMock) as mock_send_init:
            mock_send_init.return_value = {"web_push": {"success": True}}
            alert, created = await create_spoilage_alert(db=db, user=user, food=food)
            initial_count = alert.reminder_count

        # Simulate 2 hours passing: set last_notification_at to 121 mins ago and next_reminder_at to 1 min ago
        alert.last_notification_at = datetime.utcnow() - timedelta(minutes=121)
        alert.next_reminder_at = datetime.utcnow() - timedelta(minutes=1)
        db.commit()

        # Run scheduler job
        with patch("app.services.notification.send", new_callable=AsyncMock) as mock_send_remind:
            mock_send_remind.return_value = {"web_push": {"success": True}}
            await job_process_repeating_alerts()

            # Refresh alert
            db.refresh(alert)
            assert alert.reminder_count == initial_count + 1
            assert alert.status == "ACTIVE"
            # Verify next reminder has been advanced by user's interval (120 mins)
            assert alert.next_reminder_at > datetime.utcnow()
            diff_from_now = (alert.next_reminder_at - datetime.utcnow()).total_seconds()
            assert 7100 < diff_from_now < 7300  # ~120 minutes in seconds

            # Verify reminder message
            mock_send_remind.assert_called_once()
            call_kwargs = mock_send_remind.call_args[1]
            assert "🚨 Food Spoilage Reminder!" in call_kwargs["title"]
            assert "Scheduler Test Spinach" in call_kwargs["message"]
    finally:
        db.close()


# =========================================================================
# 4. Persistence Across Backend Restarts
# =========================================================================
def test_persistence_across_restarts():
    # Session 1: Create food and alert
    db1 = SessionLocal()
    user = db1.query(User).filter(User.email == "demo@smartfridge.com").first()
    food = create_test_food(db1, user.id, name="Persistent Milk Bottle", freshness="Rotten")
    alert = Alert(
        user_id=user.id,
        food_item_id=food.id,
        zone_id=food.zone_id,
        alert_type="Food Spoilage Alert",
        severity="critical",
        title="🚨 Food Spoilage Alert! Persistent Milk Bottle is Spoiled",
        message="Your Persistent Milk Bottle is spoiled.",
        status="ACTIVE",
        confidence_score=0.95,
        is_read=False,
        is_resolved=False,
        last_notification_at=datetime.utcnow(),
        next_reminder_at=datetime.utcnow() + timedelta(minutes=120),
        reminder_count=3,
        action_recommended="Remove or inspect this food item"
    )
    db1.add(alert)
    db1.commit()
    alert_id = alert.id
    db1.close()  # Simulate backend restart by closing session completely

    # Session 2: Fresh connection simulating post-restart state
    db2 = SessionLocal()
    try:
        reloaded_alert = db2.query(Alert).filter(Alert.id == alert_id).first()
        assert reloaded_alert is not None
        assert reloaded_alert.status == "ACTIVE"
        assert reloaded_alert.reminder_count == 3
        assert reloaded_alert.confidence_score == 0.95
        assert reloaded_alert.next_reminder_at is not None
        assert reloaded_alert.action_recommended == "Remove or inspect this food item"
    finally:
        db2.close()


# =========================================================================
# 5. "Remove Food" Workflow via API
# =========================================================================
def test_remove_food_workflow():
    token = get_auth_token()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        food = create_test_food(db, user.id, name="Item to Remove", freshness="Rotten")
        alert = Alert(
            user_id=user.id,
            food_item_id=food.id,
            zone_id=food.zone_id,
            alert_type="Food Spoilage Alert",
            severity="critical",
            title="🚨 Food Spoilage Alert! Item to Remove",
            message="Item to Remove is spoiled.",
            status="ACTIVE",
            is_read=False,
            is_resolved=False,
            next_reminder_at=datetime.utcnow() + timedelta(minutes=120)
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id
        food_id = food.id
    finally:
        db.close()

    with TestClient(app) as client:
        # User taps "Remove Food"
        res = client.post(
            f"/api/alerts/{alert_id}/remove-food",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200, f"Remove food failed: {res.text}"
        data = res.json()
        assert data["alert"]["status"] == "REMOVED"
        assert data["alert"]["is_resolved"] is True
        assert data["alert"]["next_reminder_at"] is None

        # Verify database changes
        db_check = SessionLocal()
        try:
            food_check = db_check.query(FoodItem).filter(FoodItem.id == food_id).first()
            assert food_check.is_discarded is True

            alert_check = db_check.query(Alert).filter(Alert.id == alert_id).first()
            assert alert_check.status == "REMOVED"
            assert alert_check.is_resolved is True
            assert alert_check.next_reminder_at is None
        finally:
            db_check.close()


# =========================================================================
# 6. "Mark as Resolved" Workflow via API
# =========================================================================
def test_resolve_alert_workflow():
    token = get_auth_token()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        food = create_test_food(db, user.id, name="Item to Resolve", freshness="Rotten")
        alert = Alert(
            user_id=user.id,
            food_item_id=food.id,
            zone_id=food.zone_id,
            alert_type="Food Spoilage Alert",
            severity="critical",
            title="🚨 Food Spoilage Alert! Item to Resolve",
            message="Item to Resolve is spoiled.",
            status="ACTIVE",
            is_read=False,
            is_resolved=False,
            next_reminder_at=datetime.utcnow() + timedelta(minutes=120)
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id
    finally:
        db.close()

    with TestClient(app) as client:
        res = client.put(
            f"/api/alerts/{alert_id}/resolve",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "success"
        assert data["alert"]["status"] == "RESOLVED"
        assert data["alert"]["is_resolved"] is True
        assert data["alert"]["next_reminder_at"] is None

        # Verify reminders stop in scheduler
        db_check = SessionLocal()
        try:
            alert_check = db_check.query(Alert).filter(Alert.id == alert_id).first()
            assert alert_check.status == "RESOLVED"
            assert alert_check.is_resolved is True
            assert alert_check.next_reminder_at is None
        finally:
            db_check.close()


# =========================================================================
# 7. User Authorization and Cross-User Data Isolation
# =========================================================================
def test_user_authorization_isolation():
    token = get_auth_token()
    db = SessionLocal()
    try:
        # Create a second user
        other_user = db.query(User).filter(User.email == "other@smartfridge.com").first()
        if not other_user:
            from app.security import get_password_hash
            other_user = User(
                email="other@smartfridge.com",
                hashed_password=get_password_hash("password123"),
                full_name="Other User"
            )
            db.add(other_user)
            db.commit()
            db.refresh(other_user)

        food = create_test_food(db, other_user.id, name="Other User Tomato", freshness="Rotten")
        alert = Alert(
            user_id=other_user.id,
            food_item_id=food.id,
            zone_id=food.zone_id,
            alert_type="Food Spoilage Alert",
            severity="critical",
            title="Other User Alert",
            message="Other user item spoiled",
            status="ACTIVE",
            is_resolved=False
        )
        db.add(alert)
        db.commit()
        other_alert_id = alert.id
    finally:
        db.close()

    # User 1 attempts to resolve or remove User 2's alert -> must return 404
    with TestClient(app) as client:
        res_resolve = client.put(
            f"/api/alerts/{other_alert_id}/resolve",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_resolve.status_code == 404

        res_remove = client.post(
            f"/api/alerts/{other_alert_id}/remove-food",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert res_remove.status_code == 404


# =========================================================================
# 8. Prediction-to-Alert Inventory Integration
# =========================================================================
def test_inventory_creation_with_rotten_triggers_alert():
    token = get_auth_token()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        zone = get_or_create_zone(db)
        zone_id = zone.id
    finally:
        db.close()

    with patch("app.services.alert_engine.send_notification", new_callable=AsyncMock) as mock_send:
        mock_send.return_value = {"web_push": {"success": True}}

        with TestClient(app) as client:
            res = client.post(
                "/api/foods",
                headers={"Authorization": f"Bearer {token}"},
                json={
                    "name": "Rotten Strawberries",
                    "category": "Fruits",
                    "item_type": "fruit",
                    "zone_id": zone_id,
                    "quantity": 1.0,
                    "unit": "box",
                    "expiry_date": (datetime.utcnow() - timedelta(days=2)).isoformat(),
                    "freshness_status": "Rotten",
                    "source": "fruit_scan"
                }
            )
            assert res.status_code == 200, f"Create food failed: {res.text}"
            food_id = res.json()["id"]

            # Verify an active Spoilage Alert was created automatically
            db_check = SessionLocal()
            try:
                alert = db_check.query(Alert).filter(
                    Alert.food_item_id == food_id,
                    Alert.alert_type == "Food Spoilage Alert",
                    Alert.status == "ACTIVE"
                ).first()
                assert alert is not None
                assert "🚨 Food Spoilage Alert!" in alert.title
                assert "Rotten Strawberries" in alert.message
                assert alert.next_reminder_at is not None
            finally:
                db_check.close()


# =========================================================================
# 9. Web Push Subscription Cleanup on Expired (410/404)
# =========================================================================
@pytest.mark.asyncio
async def test_expired_subscription_cleanup():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        user.push_subscription = json.dumps({"endpoint": "https://push.example.com/expired-endpoint"})
        user.push_notifications_enabled = True
        db.commit()

        # Mock pywebpush.webpush throwing WebPushException with response 410 Gone
        from pywebpush import WebPushException
        mock_response = MagicMock()
        mock_response.status_code = 410

        with patch("pywebpush.webpush") as mock_webpush:
            mock_webpush.side_effect = WebPushException("Subscription has expired or is invalid", response=mock_response)

            with pytest.raises(WebPushException):
                await notification.dispatch_web_push(
                    subscription_json=user.push_subscription,
                    title="Test Alert",
                    message="Test Message",
                    user=user,
                    db=db
                )

            # Verify subscription was automatically cleared from user model
            db.refresh(user)
            assert user.push_subscription is None
            assert user.push_notifications_enabled is False
    finally:
        db.close()


# =========================================================================
# 10. Settings API for Spoilage Preferences & Unsubscribe
# =========================================================================
def test_spoilage_settings_and_unsubscribe_api():
    token = get_auth_token()
    with TestClient(app) as client:
        # 1. Verify get settings contains spoilage fields
        res = client.get("/api/settings", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200
        user_settings = res.json()["user"]
        assert "spoilage_reminder_enabled" in user_settings
        assert "spoilage_reminder_interval_minutes" in user_settings
        assert "push_for_spoilage" in user_settings

        # 2. Update reminder interval to 15 minutes (test mode) and verify persistence
        res_update = client.put(
            "/api/settings",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "spoilage_reminder_interval_minutes": 15,
                "push_for_spoilage": True,
                "spoilage_reminder_enabled": True
            }
        )
        assert res_update.status_code == 200

        # Verify re-fetch has 15 minutes
        res_verify = client.get("/api/settings", headers={"Authorization": f"Bearer {token}"})
        assert res_verify.json()["user"]["spoilage_reminder_interval_minutes"] == 15

        # 3. Unsubscribe from push
        res_unsub = client.post("/api/settings/unsubscribe-push", headers={"Authorization": f"Bearer {token}"})
        assert res_unsub.status_code == 200
        assert res_unsub.json()["status"] == "unsubscribed"

        # Verify user has no push subscription
        res_after = client.get("/api/settings", headers={"Authorization": f"Bearer {token}"})
        assert res_after.json()["user"]["has_push_subscription"] is False


# =========================================================================
# 11. Requirement Tests: Timing, Provider Errors, and Format Verification
# =========================================================================
@pytest.mark.asyncio
async def test_no_reminder_sent_before_scheduled_time():
    """
    Verifies that no reminder SMS is sent before its scheduled 2-hour time.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        food = create_test_food(db, user.id, name="Early Test Apple", freshness="Rotten")
        now = datetime.utcnow()
        alert = Alert(
            user_id=user.id,
            food_item_id=food.id,
            zone_id=food.zone_id,
            alert_type="Food Spoilage Alert",
            severity="critical",
            title="🚨 Food Spoilage Alert! Early Test Apple",
            message="Early Test Apple is spoiled.",
            status="ACTIVE",
            is_read=False,
            is_resolved=False,
            last_notification_at=now - timedelta(minutes=60),
            next_reminder_at=now + timedelta(minutes=60),  # 1 hour in future (not due yet!)
            reminder_count=1
        )
        db.add(alert)
        db.commit()
        alert_id = alert.id

        with patch("app.services.notification.dispatch_sms", new_callable=AsyncMock) as mock_dispatch:
            await job_process_repeating_alerts()
            # Must NOT be called because reminder is not due yet
            mock_dispatch.assert_not_called()

        refreshed = db.query(Alert).filter(Alert.id == alert_id).first()
        assert refreshed.reminder_count == 1
        db.delete(refreshed)
        db.commit()
    finally:
        db.close()


def test_sms_formatting_exact_user_specification():
    """
    Verifies that SMS alert formatting matches user examples exactly:
    - Initial: 'SMART FRIDGE ALERT: Your Apple in Zone A is detected as spoiled. Please inspect and remove it from your fridge. Detection time: 10:00 AM.'
    - Reminder: 'SMART FRIDGE REMINDER: Your Apple in Zone A is still marked as spoiled. Please remove it from the fridge. This is reminder 2.'
    """
    from app.services.notification import format_sms_alert

    # 1. Initial Spoilage Alert
    initial_msg = format_sms_alert(
        title="Food Spoilage Alert",
        message="Your Apple is spoiled",
        food_name="Apple",
        zone_name="Zone A",
        alert_type="Food Spoilage Alert",
        status="spoiled",
        repeat_count=1,
        detection_time="10:00 AM"
    )
    expected_initial = "SMART FRIDGE ALERT: Your Apple in Zone A is detected as spoiled. Please inspect and remove it from your fridge. Detection time: 10:00 AM."
    assert initial_msg == expected_initial
    assert len(initial_msg) <= 160

    # 2. Reminder 2
    reminder_msg = format_sms_alert(
        title="Food Spoilage Reminder",
        message="Your Apple is still spoiled",
        food_name="Apple",
        zone_name="Zone A",
        alert_type="Food Spoilage Alert",
        status="spoiled",
        repeat_count=2
    )
    expected_reminder = "SMART FRIDGE REMINDER: Your Apple in Zone A is still marked as spoiled. Please remove it from the fridge. This is reminder 2."
    assert reminder_msg == expected_reminder
    assert len(reminder_msg) <= 160


@pytest.mark.asyncio
async def test_provider_failures_recorded_and_handled():
    """
    Verifies that SMS provider errors (e.g., Twilio HTTP 400 rejection) are
    handled gracefully, do not crash the application, and record failed status in NotificationLog.
    """
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        user.phone_number = "+15551234567"
        user.sms_notifications_enabled = True
        db.commit()

        with patch("app.services.notification.settings.SMS_ENABLED", True), \
             patch("app.services.notification.settings.TWILIO_ENABLED", True), \
             patch("app.services.notification.settings.TWILIO_ACCOUNT_SID", "ACtest1234567890abcdef1234567890"), \
             patch("app.services.notification.settings.TWILIO_AUTH_TOKEN", "authtest1234567890abcdef"), \
             patch("app.services.notification.settings.TWILIO_FROM_NUMBER", "+15005550006"), \
             patch("app.services.notification.Client") as mock_twilio_cls:
            mock_client = MagicMock()
            mock_twilio_cls.return_value = mock_client
            mock_client.messages.create.side_effect = Exception("Twilio error [21608]: The number is unverified in trial mode.")

            res = await notification.send(
                user=user,
                title="Failure Test Alert",
                message="Test Message",
                channel="sms",
                db=db
            )
            # Must return results without raising unhandled exception
            assert "sms" in res
            assert res["sms"]["success"] is False
            assert "21608" in str(res["sms"]["error"])

            # Verify NotificationLog recorded the failure
            log = db.query(NotificationLog).filter(
                NotificationLog.user_id == user.id,
                NotificationLog.channel == "sms"
            ).order_by(NotificationLog.created_at.desc()).first()
            assert log is not None
            assert log.status == "failed"
            assert "21608" in log.error_message
    finally:
        db.close()


def test_test_sms_endpoint_protected():
    """
    Verifies that POST /api/settings/test-sms requires authentication.
    """
    with patch("app.services.notification.Client") as mock_twilio_cls, \
         patch("app.services.notification.settings.TWILIO_ENABLED", True), \
         patch("app.services.notification.settings.TWILIO_ACCOUNT_SID", "ACmock1234567890abcdef1234567890"), \
         patch("app.services.notification.settings.TWILIO_AUTH_TOKEN", "authtest1234567890abcdef"), \
         patch("app.services.notification.settings.TWILIO_FROM_NUMBER", "+15005550006"):
        mock_client = MagicMock()
        mock_twilio_cls.return_value = mock_client
        mock_msg = MagicMock()
        mock_msg.sid = "SMprotected123"
        mock_msg.status = "queued"
        mock_msg.error_code = None
        mock_msg.error_message = None
        mock_client.messages.create.return_value = mock_msg

        with TestClient(app) as client:
            # Unauthorized call without token must return 401
            res = client.post("/api/settings/test-sms")
            assert res.status_code == 401

            # Authorized call succeeds and uses configured recipient number
            token = get_auth_token()
            res_auth = client.post("/api/settings/test-sms?phone_number=%2B15551234567", headers={"Authorization": f"Bearer {token}"})
            assert res_auth.status_code == 200
            data = res_auth.json()
            assert data["channel"] == "sms"
            assert "+15551234567" in data["recipient"]


@pytest.mark.asyncio
async def test_distinguishable_evidence_types_and_serialization():
    """
    Verifies that expiration-date spoilage alerts and ML freshness spoilage alerts
    are cleanly distinguishable, preserve their distinct evidence types and details,
    and are serialized accurately through the alerts API.
    """
    token = get_auth_token()
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
        now = datetime.utcnow()

        # 1. Date-based expired item
        expired_milk = create_test_food(db, user.id, name="Evidence Test Milk", freshness="Fresh", expiry_days=-2)
        # 2. ML Freshness-based rotten item (freshness detected as Rotten)
        rotten_tomato = create_test_food(db, user.id, name="Evidence Test Tomato", freshness="Rotten", expiry_days=5)

        with patch("app.services.alert_engine.send_notification", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = {"web_push": {"success": True}}

            alert_date, _ = await create_spoilage_alert(
                db=db,
                user=user,
                food=expired_milk,
                confidence=1.0,
                evidence_type="expiration_date",
                evidence_details="Passed recorded expiration date (2 days ago)."
            )

            alert_ml, _ = await create_spoilage_alert(
                db=db,
                user=user,
                food=rotten_tomato,
                confidence=0.94,
                evidence_type="freshness_assessment",
                evidence_details="Freshness assessment indicates spoilage with 94% confidence."
            )

            # Assert database model fields
            assert alert_date.evidence_type == "expiration_date"
            assert "expiration date" in alert_date.evidence_details
            assert alert_date.confidence_score == 1.0

            assert alert_ml.evidence_type == "freshness_assessment"
            assert "Freshness assessment" in alert_ml.evidence_details
            assert alert_ml.confidence_score == 0.94

        # Test API serialization for frontend consumption
        with TestClient(app) as client:
            res = client.get("/api/alerts", headers={"Authorization": f"Bearer {token}"})
            assert res.status_code == 200
            alerts_data = res.json()
            alert_map = {a["id"]: a for a in alerts_data}

            assert alert_date.id in alert_map
            assert alert_map[alert_date.id]["evidence_type"] == "expiration_date"
            assert alert_map[alert_date.id]["evidence_details"] == "Passed recorded expiration date (2 days ago)."

            assert alert_ml.id in alert_map
            assert alert_map[alert_ml.id]["evidence_type"] == "freshness_assessment"
            assert alert_map[alert_ml.id]["evidence_details"] == "Freshness assessment indicates spoilage with 94% confidence."
            assert alert_map[alert_ml.id]["confidence_score"] == 0.94
    finally:
        db.close()


