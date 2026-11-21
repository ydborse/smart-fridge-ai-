import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models import User, Zone, NotificationLog, FoodItem
from app.schemas import UserOut, UserUpdate, NotificationLogOut
from app.services import notification
from app.security import get_current_user, get_required_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings & Notifications"])


def _build_realtime_food_summary(db: Session, user: User):
    now = datetime.utcnow()
    lead_days = getattr(user, "alert_lead_days", 2) or 2
    cutoff = now + timedelta(days=lead_days)

    items = (
        db.query(FoodItem)
        .filter(
            FoodItem.user_id == user.id,
            FoodItem.is_used == False,
            FoodItem.is_discarded == False,
        )
        .order_by(FoodItem.expiry_date.asc())
        .all()
    )

    urgent = [
        f for f in items
        if (f.freshness_status in ("Rotten", "Expired", "Expiring Soon", "Overripe"))
        or (f.expiry_date and f.expiry_date <= cutoff)
    ][:8]

    selected = urgent if urgent else items[:5]
    grouped_food_items = []
    lines = []

    for food in selected:
        zone_name = food.zone.name if food.zone else "Fridge"
        expiry = food.expiry_date.strftime("%b %d, %Y") if food.expiry_date else "Unknown"
        status = food.freshness_status or "Fresh"
        if food.expiry_date and food.expiry_date < now:
            reason = f"Past recorded expiry date ({expiry})"
        elif food.expiry_date and food.expiry_date <= cutoff:
            reason = f"Expiring soon ({expiry})"
        else:
            reason = f"Currently tracked ({status})"

        grouped_food_items.append({
            "name": food.name,
            "category": food.category or "Food",
            "status": status,
            "zone_name": zone_name,
            "expiry_date": expiry,
            "reason": reason,
            "alert_type": "Fridge Food Summary",
            "item_type": getattr(food, "item_type", None),
        })
        lines.append(f"• {food.name} ({zone_name}) — {status} | Expiry: {expiry}")

    count = len(grouped_food_items)
    if count > 0:
        title = (
            f"Smart Fridge Summary: {count} item(s) need attention"
            if urgent
            else f"Smart Fridge Inventory Summary ({count} items)"
        )
        message = (
            "Here is your live Smart Fridge food condition summary:\n\n"
            + "\n".join(lines)
        )
    else:
        title = "Smart Fridge Summary: All Clear"
        message = "Your refrigerator has no expiring or spoiled items right now."

    return title, message, grouped_food_items


@router.get("")
def get_user_settings(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    return {
        "user": {
            "id": current_user.id,
            "email": current_user.email,
            "full_name": current_user.full_name,
            "phone_number": current_user.phone_number,
            "email_notifications_enabled": current_user.email_notifications_enabled,
            "push_notifications_enabled": current_user.push_notifications_enabled,
            "sms_notifications_enabled": current_user.sms_notifications_enabled,
            "telegram_notifications_enabled": getattr(current_user, "telegram_notifications_enabled", True) if getattr(current_user, "telegram_notifications_enabled", None) is not None else True,
            "telegram_chat_id": notification.resolve_telegram_chat_id(user=current_user) or "Not Configured",
            "has_push_subscription": bool(current_user.push_subscription),
            "email_for_expiring": current_user.email_for_expiring,
            "email_for_expired": current_user.email_for_expired,
            "email_daily_digest": current_user.email_daily_digest,
            "push_for_expiring": current_user.push_for_expiring,
            "push_for_expired": current_user.push_for_expired,
            "push_for_temperature": getattr(current_user, "push_for_temperature", True) if getattr(current_user, "push_for_temperature", None) is not None else True,
            "spoilage_reminder_enabled": getattr(current_user, "spoilage_reminder_enabled", True) if getattr(current_user, "spoilage_reminder_enabled", None) is not None else True,
            "spoilage_reminder_interval_minutes": getattr(current_user, "spoilage_reminder_interval_minutes", 120) or 120,
            "push_for_spoilage": getattr(current_user, "push_for_spoilage", True) if getattr(current_user, "push_for_spoilage", None) is not None else True,
            "sms_for_critical": current_user.sms_for_critical,
            "sms_for_expiring": getattr(current_user, "sms_for_expiring", False) or False,
            "sms_for_expired": getattr(current_user, "sms_for_expired", True) if getattr(current_user, "sms_for_expired", None) is not None else True,
            "sms_for_temperature": getattr(current_user, "sms_for_temperature", True) if getattr(current_user, "sms_for_temperature", None) is not None else True,
            "sms_for_dairy": getattr(current_user, "sms_for_dairy", True) if getattr(current_user, "sms_for_dairy", None) is not None else True,
            "sms_repeat_interval_minutes": getattr(current_user, "sms_repeat_interval_minutes", 15) or 15,
            "sms_max_duration_minutes": getattr(current_user, "sms_max_duration_minutes", 120) or 120,
            "alert_lead_days": current_user.alert_lead_days,
            "quiet_hours_start": current_user.quiet_hours_start,
            "quiet_hours_end": current_user.quiet_hours_end,
            "audit_day": current_user.audit_day,
            "audit_time": current_user.audit_time
        },
        "telegram_system_status": {
            "provider": "telegram",
            "enabled": bool(settings.TELEGRAM_ENABLED),
            "configured": bool(settings.telegram_configured),
            "chat_id": notification.resolve_telegram_chat_id(user=current_user) or "Not Configured",
            "token_present": bool(settings.TELEGRAM_BOT_TOKEN and "PASTE_YOUR" not in settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_BOT_TOKEN != "your_telegram_bot_token"),
            "token_length": len(settings.TELEGRAM_BOT_TOKEN) if settings.TELEGRAM_BOT_TOKEN else 0,
            "chat_id_present": bool(settings.TELEGRAM_CHAT_ID and "PASTE_YOUR" not in str(settings.TELEGRAM_CHAT_ID) and str(settings.TELEGRAM_CHAT_ID) not in ["your_telegram_chat_id", "554433221"])
        },
        "sms_system_status": {
            "provider": "telegram" if settings.telegram_configured else getattr(settings, "SMS_PROVIDER", "telegram"),
            "enabled": bool(settings.TELEGRAM_ENABLED) or bool(getattr(settings, "TWILIO_ENABLED", False)),
            "configured": bool(settings.telegram_configured),
            "twilio_configured": bool(
                settings.TWILIO_ACCOUNT_SID and
                settings.TWILIO_AUTH_TOKEN and
                (settings.TWILIO_FROM_NUMBER or settings.TWILIO_MESSAGING_SERVICE_SID) and
                settings.TWILIO_ACCOUNT_SID.startswith("AC") and
                "xxxxxxxx" not in settings.TWILIO_ACCOUNT_SID and
                "your_twilio" not in settings.TWILIO_AUTH_TOKEN and
                settings.TWILIO_AUTH_TOKEN.strip() != ""
            ),
            "from_number": "Telegram Bot" if settings.telegram_configured else (settings.TWILIO_FROM_NUMBER or "Not Configured"),
            "to_number": getattr(settings, "TELEGRAM_CHAT_ID", None) or getattr(settings, "TWILIO_TO_NUMBER", None) or "Not Configured",
            "default_repeat_interval": getattr(settings, "SMS_REMINDER_INTERVAL_MINUTES", 120),
            "default_max_duration": settings.SMS_DEFAULT_MAX_DURATION_MINUTES
        },
        "zones": [
            {
                "id": z.id,
                "name": z.name,
                "code": z.code,
                "target_temp_min": z.target_temp_min,
                "target_temp_max": z.target_temp_max,
                "target_humidity_min": z.target_humidity_min,
                "target_humidity_max": z.target_humidity_max,
                "description": z.description
            }
            for z in zones
        ]
    }


@router.put("")
def update_user_settings(
    settings_in: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        update_data = settings_in.model_dump(exclude_unset=True)
    except AttributeError:
        update_data = settings_in.dict(exclude_unset=True)

    if "phone_number" in update_data and update_data["phone_number"]:
        from app.services.notification import normalize_phone_number
        update_data["phone_number"] = normalize_phone_number(update_data["phone_number"])

    if "sms_enabled" in update_data and update_data["sms_enabled"] is not None:
        update_data["sms_notifications_enabled"] = bool(update_data["sms_enabled"])

    for field, val in update_data.items():
        if hasattr(current_user, field):
            setattr(current_user, field, val)

    # If SMS notifications were disabled, clear pending repeats on open alerts
    if ("sms_notifications_enabled" in update_data and not update_data["sms_notifications_enabled"]) or \
       ("sms_enabled" in update_data and not update_data["sms_enabled"]):
        from app.models import Alert
        db.query(Alert).filter(
            Alert.user_id == current_user.id,
            Alert.is_resolved == False
        ).update({"next_sms_scheduled_at": None})

    # If spoilage reminder interval updated, reschedule active open alerts
    if "spoilage_reminder_interval_minutes" in update_data and update_data["spoilage_reminder_interval_minutes"]:
        new_int = int(update_data["spoilage_reminder_interval_minutes"])
        from app.models import Alert
        now = datetime.utcnow()
        open_alerts = db.query(Alert).filter(
            Alert.user_id == current_user.id,
            Alert.is_resolved == False,
            Alert.status == "ACTIVE"
        ).all()
        for a in open_alerts:
            a.next_reminder_at = now + timedelta(minutes=new_int)
            a.next_sms_scheduled_at = now + timedelta(minutes=new_int)

    # If spoilage reminders disabled, silence pending next reminders
    if "spoilage_reminder_enabled" in update_data and not update_data["spoilage_reminder_enabled"]:
        from app.models import Alert
        db.query(Alert).filter(
            Alert.user_id == current_user.id,
            Alert.is_resolved == False
        ).update({"next_reminder_at": None})

    db.commit()
    db.refresh(current_user)
    return {
        "message": "Settings updated successfully",
        "user": current_user,
        "phone_number": current_user.phone_number,
        "sms_repeat_interval_minutes": current_user.sms_repeat_interval_minutes,
        "sms_max_duration_minutes": current_user.sms_max_duration_minutes,
        "sms_notifications_enabled": current_user.sms_notifications_enabled,
        "sms_enabled": current_user.sms_notifications_enabled,
        "spoilage_reminder_interval_minutes": current_user.spoilage_reminder_interval_minutes,
        "spoilage_reminder_enabled": current_user.spoilage_reminder_enabled
    }


@router.get("/vapid-public-key")
def get_vapid_public_key():
    return {
        "public_key": settings.VAPID_PUBLIC_KEY,
        "enabled": settings.WEB_PUSH_ENABLED
    }


@router.post("/subscribe-push")
def subscribe_web_push(
    payload: Dict[str, Any],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.push_subscription = json.dumps(payload)
    current_user.push_notifications_enabled = True
    db.commit()
    return {"status": "subscribed", "message": "Device successfully registered for Web Push notifications"}


@router.post("/unsubscribe-push")
def unsubscribe_web_push(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    current_user.push_subscription = None
    current_user.push_notifications_enabled = False
    db.commit()
    return {"status": "unsubscribed", "message": "Successfully unsubscribed from Web Push notifications"}


@router.post("/test-email")
async def send_test_email(
    recipient: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Dispatches a live grouped food summary HTML email."""
    target_email = recipient or current_user.email
    if not target_email:
        raise HTTPException(status_code=400, detail="No email address specified")

    title, message, grouped_items = _build_realtime_food_summary(db, current_user)
    user_copy = current_user
    if recipient:
        user_copy.email = recipient

    res = await notification.send(
        user=user_copy,
        title=title,
        message=message,
        channel="email",
        metadata={
            "alert_type": "Live Fridge Summary",
            "food_items": grouped_items,
        },
        db=db
    )
    return {
        "status": "success",
        "channel": "email",
        "recipient": target_email,
        "result": res.get("email", {})
    }


@router.post("/test-push")
async def send_test_push(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not current_user.push_subscription:
        raise HTTPException(
            status_code=400,
            detail="No Web Push subscription found for this account. Click 'Enable Phone Notifications' first."
        )

    res = await notification.send(
        user=current_user,
        title="Smart Fridge Web Push",
        message="Web Push notification test successful! Your phone/browser is now linked.",
        channel="web_push",
        metadata={"action_url": f"{settings.APP_URL}/foods"},
        db=db
    )
    return {
        "status": "success",
        "channel": "web_push",
        "result": res.get("web_push", {})
    }


@router.get("/telegram-diagnostic")
async def check_telegram_diagnostic(current_user: User = Depends(get_current_user)):
    return await notification.get_telegram_diagnostic()


@router.post("/test-telegram")
async def send_test_telegram(
    chat_id: Optional[str] = None,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    """Dispatches a live grouped food summary via the Telegram Bot API."""
    target_chat = notification.resolve_telegram_chat_id(user=current_user, override_chat_id=chat_id)
    if not target_chat or "PASTE_YOUR" in str(target_chat):
        raise HTTPException(
            status_code=400,
            detail="No Telegram Chat ID configured. Please set TELEGRAM_CHAT_ID in backend/.env with your chat ID."
        )

    title, test_message, grouped_items = _build_realtime_food_summary(db, current_user)

    try:
        res = await notification.send(
            user=current_user,
            title=title,
            message=test_message,
            channel="telegram",
            metadata={
                "chat_id": target_chat,
                "alert_type": "Live Fridge Summary",
                "food_items": grouped_items,
            },
            db=db,
            repeat_count=1
        )
    except Exception as e:
        safe_msg = notification.sanitize_telegram_token(str(e))
        raise HTTPException(status_code=502, detail=f"Telegram delivery failed: {safe_msg}")

    tg_res = res.get("telegram", {})
    success = tg_res.get("success", False)
    if not success:
        err = tg_res.get("error") or tg_res.get("detail") or "Telegram message delivery failed"
        raise HTTPException(status_code=502, detail=f"Telegram delivery failed: {err}")

    return {
        "status": "success",
        "channel": "telegram",
        "recipient": tg_res.get("recipient", target_chat),
        "provider": "telegram",
        "provider_message_id": tg_res.get("provider_message_id"),
        "delivery_status": tg_res.get("status", "delivered"),
        "is_simulated": False,
        "message": tg_res.get("formatted_message", test_message),
        "formatted_message": tg_res.get("formatted_message", test_message),
        "detail": tg_res.get("detail", "Message confirmed delivered by Telegram Bot API"),
        "result": tg_res
    }


@router.post("/test-sms")
async def send_test_sms(
    phone_number: Optional[str] = None,
    current_user: User = Depends(get_required_user),
    db: Session = Depends(get_db)
):
    target_phone = phone_number or current_user.phone_number or getattr(settings, "TWILIO_TO_NUMBER", None) or getattr(settings, "SMS_TO_NUMBER", None)
    if not target_phone:
        raise HTTPException(status_code=400, detail="No phone number configured. Please enter a mobile number in E.164 format (e.g., +91 9876543210) or configure TWILIO_TO_NUMBER in .env.")

    user_copy = current_user
    if target_phone:
        user_copy.phone_number = target_phone

    title, test_message, grouped_items = _build_realtime_food_summary(db, current_user)

    res = await notification.send(
        user=user_copy,
        title=title,
        message=test_message,
        channel="sms",
        metadata={"alert_type": "Live Fridge Summary", "food_items": grouped_items},
        db=db,
        repeat_count=1
    )
    sms_res = res.get("sms", {})
    success = sms_res.get("success", False)
    if not success:
        err = sms_res.get("error") or sms_res.get("detail") or "Twilio SMS transmission failed"
        raise HTTPException(status_code=502, detail=f"SMS delivery failed: {err}")

    return {
        "status": "success" if success else "failed",
        "channel": "sms",
        "recipient": sms_res.get("recipient", target_phone),
        "provider": sms_res.get("provider", "twilio"),
        "provider_message_id": sms_res.get("provider_message_id"),
        "delivery_status": sms_res.get("status", "sent"),
        "is_simulated": sms_res.get("is_simulated", False),
        "message": sms_res.get("formatted_message", test_message),
        "formatted_message": sms_res.get("formatted_message", test_message),
        "detail": sms_res.get("detail", ""),
        "result": sms_res
    }


@router.get("/notifications-log", response_model=List[NotificationLogOut])
def get_notification_logs(
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    logs = db.query(NotificationLog).filter(
        NotificationLog.user_id == current_user.id
    ).order_by(NotificationLog.created_at.desc()).limit(limit).all()
    return logs