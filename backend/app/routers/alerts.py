from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Alert, User
from app.schemas import AlertOut
from app.services.alert_engine import evaluate_food_alerts, evaluate_compatibility_alerts, evaluate_temperature_alerts
from app.services import notification
from app.security import get_current_user

router = APIRouter(prefix="/alerts", tags=["Alerts & Notifications"])

from datetime import datetime
from app.models import FoodItem, ActivityHistory
from app.schemas import AlertOut, SpoilageAlertRequest
from app.services.alert_engine import create_spoilage_alert

def serialize_alert(a: Alert) -> dict:
    zone_name = a.zone.name if a.zone else (a.food_item.zone.name if a.food_item and a.food_item.zone else None)
    return {
        "id": a.id,
        "food_item_id": a.food_item_id,
        "food_item_name": a.food_item.name if a.food_item else None,
        "food_category": a.food_item.category if a.food_item else None,
        "food_freshness": a.food_item.freshness_status if a.food_item else None,
        "food_image": a.food_item.image_path if a.food_item else None,
        "zone_id": a.zone_id or (a.food_item.zone_id if a.food_item else None),
        "zone_name": zone_name,
        "alert_type": a.alert_type,
        "severity": a.severity,
        "title": a.title,
        "message": a.message,
        "status": getattr(a, "status", None) or ("RESOLVED" if a.is_resolved else "ACTIVE"),
        "is_read": a.is_read,
        "is_resolved": getattr(a, "is_resolved", False) or False,
        "resolved_at": getattr(a, "resolved_at", None),
        "confidence_score": getattr(a, "confidence_score", None),
        "last_notification_at": getattr(a, "last_notification_at", None) or getattr(a, "last_sms_sent_at", None),
        "next_reminder_at": getattr(a, "next_reminder_at", None) or getattr(a, "next_sms_scheduled_at", None),
        "reminder_count": getattr(a, "reminder_count", 0) or getattr(a, "sms_repeat_count", 0) or 0,
        "action_recommended": getattr(a, "action_recommended", "Remove or inspect this food item") or "Remove or inspect this food item",
        "first_sms_sent_at": getattr(a, "first_sms_sent_at", None),
        "last_sms_sent_at": getattr(a, "last_sms_sent_at", None),
        "next_sms_scheduled_at": getattr(a, "next_sms_scheduled_at", None),
        "sms_repeat_count": getattr(a, "sms_repeat_count", 0) or 0,
        "evidence_type": getattr(a, "evidence_type", None) or "freshness_assessment",
        "evidence_details": getattr(a, "evidence_details", None),
        "channel_sent": a.channel_sent,
        "created_at": a.created_at
    }

@router.get("", response_model=List[AlertOut])
def get_alerts(
    alert_type: Optional[str] = None,
    is_read: Optional[bool] = None,
    is_resolved: Optional[bool] = None,
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Alert).filter(Alert.user_id == current_user.id)
    if alert_type:
        query = query.filter(Alert.alert_type == alert_type)
    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)
    if is_resolved is not None:
        query = query.filter(Alert.is_resolved == is_resolved)
    if status:
        query = query.filter(Alert.status == status.upper())

    alerts = query.order_by(Alert.created_at.desc()).all()
    return [serialize_alert(a) for a in alerts]

@router.get("/active-spoilage", response_model=List[AlertOut])
def get_active_spoilage_alerts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns only active, unresolved spoilage alerts for the current user.
    """
    alerts = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.is_resolved == False,
        Alert.alert_type.in_(["Food Spoilage Alert", "Expired / Remove Now"])
    ).order_by(Alert.created_at.desc()).all()
    return [serialize_alert(a) for a in alerts]

@router.post("/spoilage", response_model=AlertOut)
async def trigger_spoilage_alert_endpoint(
    req: SpoilageAlertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Directly creates or activates a spoilage alert for a tracked food item.
    Dispatches immediate mobile notification and schedules 2-hour repeating reminders.
    """
    food = db.query(FoodItem).filter(
        FoodItem.id == req.food_item_id,
        FoodItem.user_id == current_user.id
    ).first()
    if not food:
        raise HTTPException(status_code=404, detail="Food item not found")

    food.freshness_status = "Rotten"
    alert, created = await create_spoilage_alert(
        db=db,
        user=current_user,
        food=food,
        confidence=1.0,
        custom_notes=req.custom_notes
    )
    return serialize_alert(alert)

@router.post("/{alert_id}/remove-food")
def remove_food_via_alert(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Confirms food removal: marks food discarded in inventory, sets alert to REMOVED,
    and cancels subsequent 2-hour reminders.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == current_user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    now = datetime.utcnow()
    food_name = "Food item"
    if alert.food_item_id:
        food = db.query(FoodItem).filter(
            FoodItem.id == alert.food_item_id,
            FoodItem.user_id == current_user.id
        ).first()
        if food:
            food_name = food.name
            food.is_discarded = True
            db.add(ActivityHistory(
                user_id=current_user.id,
                action="discarded",
                food_item_name=food.name,
                quantity=food.quantity,
                unit=food.unit,
                estimated_cost=food.estimated_cost,
                timestamp=now
            ))

    alert.status = "REMOVED"
    alert.is_resolved = True
    alert.is_read = True
    alert.resolved_at = now
    alert.next_reminder_at = None
    alert.next_sms_scheduled_at = None
    db.commit()

    return {
        "status": "success",
        "message": f"Confirmed: {food_name} removed from fridge. Alert resolved and reminders cancelled.",
        "alert": serialize_alert(alert)
    }

@router.put("/{alert_id}/resolve")
def resolve_alert_endpoint(
    alert_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == current_user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    now = datetime.utcnow()
    alert.status = "RESOLVED"
    alert.is_resolved = True
    alert.is_read = True
    alert.resolved_at = now
    alert.next_reminder_at = None
    alert.next_sms_scheduled_at = None
    db.commit()
    return {
        "status": "success",
        "message": "Alert resolved successfully. Future reminders cancelled.",
        "alert_id": alert_id,
        "status_code": "RESOLVED",
        "is_resolved": True,
        "resolved_at": alert.resolved_at,
        "next_reminder_at": None,
        "next_sms_scheduled_at": None,
        "alert": serialize_alert(alert)
    }

@router.put("/{alert_id}/read")
def mark_alert_read(alert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == current_user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.is_read = True
    alert.next_sms_scheduled_at = None
    db.commit()
    return {"message": "Alert marked as read"}

@router.put("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Alert).filter(Alert.user_id == current_user.id, Alert.is_read == False).update({
        "is_read": True,
        "next_sms_scheduled_at": None
    })
    db.commit()
    return {"message": "All alerts marked as read"}


@router.delete("/{alert_id}")
def delete_alert(alert_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == current_user.id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    db.delete(alert)
    db.commit()
    return {"message": "Alert deleted"}

@router.post("/evaluate")
async def trigger_alert_evaluation(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    f_alerts = await evaluate_food_alerts(db, current_user)
    c_alerts = await evaluate_compatibility_alerts(db, current_user)
    t_alerts = await evaluate_temperature_alerts(db, current_user)
    total_new = len(f_alerts) + len(c_alerts) + len(t_alerts)
    return {
        "status": "success",
        "new_alerts_count": total_new,
        "message": f"Evaluated alert rules. {total_new} new alert(s) generated."
    }

@router.get("/scheduler-status")
def get_scheduler_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Observable backend scheduler status endpoint:
    Returns whether APScheduler is actively running, active recurring spoilage incidents count,
    configured interval, and next run times.
    """
    from app.services.scheduler import scheduler
    from app.models import Alert
    active_spoilage_count = db.query(Alert).filter(
        Alert.user_id == current_user.id,
        Alert.is_resolved == False,
        Alert.alert_type.in_(["Food Spoilage Alert", "Expired / Remove Now"])
    ).count()

    jobs = []
    if scheduler.running:
        for j in scheduler.get_jobs():
            jobs.append({
                "id": j.id,
                "name": getattr(j, "name", j.id),
                "next_run_time": j.next_run_time.isoformat() if getattr(j, "next_run_time", None) else None
            })

    return {
        "status": "online" if scheduler.running else "offline",
        "scheduler_running": scheduler.running,
        "active_spoilage_incidents": active_spoilage_count,
        "recurring_interval_minutes": getattr(current_user, "spoilage_reminder_interval_minutes", 120) or 120,
        "reminders_enabled": getattr(current_user, "spoilage_reminder_enabled", True),
        "jobs": jobs
    }

@router.post("/test-notification")
async def send_test_notification(
    channel: str = Query("all", description="Channel: email, web_push, sms, or all"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        res = await notification.send(
            user=current_user,
            title="Smart Fridge Test Alert ✅",
            message="This is a test notification from your Smart Refrigerator Assistant. Alerts for expiring foods, gas compatibility, and temperature will arrive here!",
            channel=channel,
            db=db
        )
    except Exception as e:
        safe_msg = notification.sanitize_telegram_token(str(e))
        return {
            "status": "failed",
            "channel": channel,
            "summary": f"Notification dispatch failed: {safe_msg}",
            "results": {
                channel: {
                    "success": False,
                    "error": safe_msg,
                    "detail": safe_msg
                }
            }
        }

    # Build human-readable summary
    summary_parts = []
    if "telegram" in res:
        tg = res["telegram"]
        msg_id = tg.get("provider_message_id")
        recipient = tg.get("recipient", "")
        if tg.get("success"):
            id_str = f" [Msg ID: {msg_id}]" if msg_id else ""
            summary_parts.append(f"Telegram: Delivered to chat {recipient}{id_str}")
        else:
            err_msg = tg.get("error") or tg.get("detail") or "Delivery failed"
            summary_parts.append(f"Telegram: {err_msg}")
    elif "sms" in res:
        sm = res["sms"]
        sid = sm.get("provider_message_id")
        provider_name = sm.get("provider", "Twilio")
        raw_status = sm.get("status", "accepted")
        if sm.get("success"):
            sid_str = f" [SID: {sid}]" if sid else ""
            summary_parts.append(f"SMS: Provider {provider_name} accepted ({raw_status}){sid_str}")
        else:
            err_msg = sm.get("error") or sm.get("detail") or "Delivery failed"
            summary_parts.append(f"SMS: {err_msg}")
    if "web_push" in res:
        wp = res["web_push"]
        if wp.get("success"):
            summary_parts.append(f"Web Push: {wp.get('provider')} accepted")
        else:
            summary_parts.append(f"Web Push: {wp.get('error') or 'Not delivered'}")
    if "email" in res:
        em = res["email"]
        if em.get("success"):
            summary_parts.append(f"Email: Accepted ({em.get('provider')})")
        else:
            summary_parts.append(f"Email: {em.get('error') or 'Failed'}")

    has_success = any(v.get("success", False) for v in res.values()) if res else False
    all_success = all(v.get("success", False) for v in res.values()) if res else True
    return {
        "status": "success" if all_success else ("partial_failure" if has_success else "failed"),
        "channel": channel,
        "summary": " | ".join(summary_parts) if summary_parts else "Notification dispatched",
        "results": res
    }
