import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings
from app.database import SessionLocal
from app.services.sensor_simulator import update_sensor_readings
from app.services.alert_engine import run_all_alert_rules
from app.services import notification
from app.models import User, FoodItem, Alert

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()
_sms_repeat_lock = asyncio.Lock()


def job_update_sensors():
    db = SessionLocal()
    try:
        update_sensor_readings(db)
    except Exception as e:
        logger.error(f"Error in sensor simulator job: {e}")
    finally:
        db.close()


async def job_check_alerts():
    db = SessionLocal()
    try:
        await run_all_alert_rules(db)
    except Exception as e:
        logger.error(f"Error in alert rules job: {e}")
    finally:
        db.close()


async def job_process_repeating_alerts():
    """
    Periodic job (running every 60s) that processes repeating SMS notifications
    for active, unresolved alerts. Enforces:
    - Configurable repeat interval (default 15 minutes)
    - 2-hour maximum cutoff (120 minutes) strictly from first_sms_sent_at
    - Immediate cancellation upon alert resolution (is_resolved=True) or acknowledgement (is_read=True)
    - Concurrency protection and anti-spam cooldown
    - Persistence across server restarts
    """
    if _sms_repeat_lock.locked():
        logger.debug("Repeating SMS processor is currently running, skipping overlapping tick.")
        return

    async with _sms_repeat_lock:
        db = SessionLocal()
        try:
            now = datetime.utcnow()
            # 1. Fetch active, unresolved spoilage alerts due for recurring reminder
            due_spoilage_alerts = db.query(Alert).filter(
                Alert.is_resolved == False,
                Alert.status == "ACTIVE",
                Alert.next_reminder_at != None,
                Alert.next_reminder_at <= now
            ).all()

            for alert in due_spoilage_alerts:
                try:
                    user = alert.user
                    if not user:
                        continue

                    # Check if spoilage reminders are enabled for this user
                    reminders_enabled = getattr(user, "spoilage_reminder_enabled", True)
                    if not reminders_enabled:
                        alert.next_reminder_at = None
                        db.commit()
                        continue

                    # Prioritize user's configured interval (default 120m / 2 hours)
                    repeat_interval = getattr(user, "spoilage_reminder_interval_minutes", None) or getattr(settings, "SMS_REMINDER_INTERVAL_MINUTES", 120) or 120

                    # Anti-spam cooldown within repeat_interval
                    min_gap = min(30, int(repeat_interval * 30))
                    if alert.last_notification_at:
                        seconds_since_last = (now - alert.last_notification_at).total_seconds()
                        if seconds_since_last < (repeat_interval * 60 - min_gap):
                            logger.debug(f"Spoilage Alert #{alert.id} within cooldown ({seconds_since_last:.0f}s). Skipping.")
                            continue

                    new_count = (alert.reminder_count or 1) + 1
                    food = alert.food_item
                    zone = alert.zone or (food.zone if food else None)
                    zone_name = zone.name if zone else "Fridge"
                    food_name = food.name if food else "Food item"
                    reason = alert.evidence_details or ("freshness assessment indicates spoilage" if alert.evidence_type != "expiration_date" else "recorded expiration date has passed")

                    remind_title = f"🚨 Food Spoilage Reminder! {food_name} in {zone_name}"
                    remind_message = f"🚨 SMART FRIDGE REMINDER (#{new_count}): Your {food_name} in {zone_name} is still marked as spoiled. Reason: {reason}. Please inspect and remove it from your fridge. This is reminder #{new_count}."

                    metadata = {
                        "alert_id": alert.id,
                        "food_item_id": food.id if food else None,
                        "food_name": food_name,
                        "category": food.category if food else None,
                        "zone_name": zone_name,
                        "status": food.freshness_status if food else "Rotten",
                        "evidence_type": alert.evidence_type,
                        "evidence_details": alert.evidence_details,
                        "reason": reason,
                        "action_recommended": "Remove or inspect this food item",
                        "action_url": f"/alerts?id={alert.id}",
                        "reminder_count": new_count
                    }

                    # Dispatch mobile reminder (Web Push, Email, SMS according to user settings)
                    await notification.send(
                        user=user,
                        title=remind_title,
                        message=remind_message,
                        channel="all",
                        metadata=metadata,
                        db=db,
                        alert_id=alert.id,
                        repeat_count=new_count
                    )

                    alert.reminder_count = new_count
                    alert.last_notification_at = now
                    alert.next_reminder_at = now + timedelta(minutes=repeat_interval)

                    # Keep SMS fields synchronized
                    alert.sms_repeat_count = new_count
                    alert.last_sms_sent_at = now
                    alert.next_sms_scheduled_at = now + timedelta(minutes=repeat_interval)

                    db.commit()
                    logger.info(
                        f"2-Hour Spoilage Reminder #{new_count} sent for Alert #{alert.id} ({food_name}). "
                        f"Next reminder scheduled: {alert.next_reminder_at}"
                    )
                except Exception as alert_err:
                    logger.error(f"Error dispatching reminder for alert #{alert.id}: {alert_err}")
                    # Advance next_reminder_at to avoid tight retry spam loops on failure
                    try:
                        db.rollback()
                        alert.next_reminder_at = now + timedelta(minutes=15)
                        db.commit()
                    except Exception:
                        db.rollback()

            # 2. Fetch any other active unresolved alerts with legacy next_sms_scheduled_at due (e.g. Temperature warnings, legacy expiry)
            due_sms_alerts = db.query(Alert).filter(
                Alert.is_resolved == False,
                Alert.is_read == False,
                Alert.next_sms_scheduled_at != None,
                Alert.next_sms_scheduled_at <= now,
                Alert.alert_type != "Food Spoilage Alert"
            ).all()

            for alert in due_sms_alerts:
                user = alert.user
                is_notif_enabled = getattr(user, "telegram_notifications_enabled", None)
                if is_notif_enabled is None:
                    is_notif_enabled = getattr(user, "sms_notifications_enabled", True)
                has_dest = bool(notification.resolve_telegram_chat_id(user=user))
                if not user or not is_notif_enabled or not has_dest:
                    alert.next_sms_scheduled_at = None
                    db.commit()
                    continue

                repeat_interval = getattr(user, "sms_repeat_interval_minutes", 15) or 15
                max_duration = getattr(user, "sms_max_duration_minutes", 120) or 120

                base_time = alert.first_sms_sent_at or alert.created_at
                elapsed_minutes = (now - base_time).total_seconds() / 60.0

                if elapsed_minutes >= max_duration:
                    logger.info(
                        f"Alert #{alert.id} reached maximum repeat duration of {max_duration}m. Stopping repeats."
                    )
                    alert.next_sms_scheduled_at = None
                    db.commit()
                    continue

                if alert.last_sms_sent_at:
                    seconds_since_last = (now - alert.last_sms_sent_at).total_seconds()
                    if seconds_since_last < (repeat_interval * 60 - 30):
                        continue

                new_repeat_count = (alert.sms_repeat_count or 1) + 1
                food = alert.food_item
                zone = alert.zone
                metadata = {
                    "alert_type": alert.alert_type,
                    "severity": alert.severity
                }
                if food:
                    metadata.update({
                        "food_name": food.name,
                        "category": food.category,
                        "status": food.freshness_status
                    })
                elif zone:
                    metadata.update({
                        "zone_name": zone.name,
                        "temperature": zone.current_temp,
                        "humidity": zone.current_humidity
                    })

                await notification.send(
                    user=user,
                    title=alert.title,
                    message=alert.message,
                    channel="telegram",
                    metadata=metadata,
                    db=db,
                    alert_id=alert.id,
                    repeat_count=new_repeat_count
                )

                alert.sms_repeat_count = new_repeat_count
                alert.last_sms_sent_at = now

                next_time = now + timedelta(minutes=repeat_interval)
                total_duration_if_next = (next_time - base_time).total_seconds() / 60.0
                if total_duration_if_next <= max_duration:
                    alert.next_sms_scheduled_at = next_time
                else:
                    alert.next_sms_scheduled_at = None

                db.commit()

        except Exception as e:
            logger.error(f"Error in job_process_repeating_alerts: {e}")
            db.rollback()
        finally:
            db.close()


async def job_daily_digest_8am():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        now = datetime.utcnow()
        for user in users:
            if not (user.email and user.email_daily_digest and user.email_notifications_enabled):
                continue
            lead_date = now + timedelta(days=user.alert_lead_days)
            expiring_items = db.query(FoodItem).filter(
                FoodItem.user_id == user.id,
                FoodItem.is_used == False,
                FoodItem.is_discarded == False,
                FoodItem.expiry_date <= lead_date
            ).all()

            if expiring_items:
                digest_items = []
                for item in expiring_items:
                    days_left = max(0, int((item.expiry_date - now).total_seconds() / 86400))
                    zone_name = item.zone.name if item.zone else "Fridge"
                    digest_items.append({
                        "id": item.id,
                        "name": item.name,
                        "zone": zone_name,
                        "days_left": days_left
                    })
                await notification.send_daily_digest(user, digest_items, db=db)
    except Exception as e:
        logger.error(f"Error in daily digest job: {e}")
    finally:
        db.close()
async def job_daily_spoilage_digest():
    """Send one grouped daily summary of unresolved spoiled/expired foods."""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()

        for user in users:
            alerts = (
                db.query(Alert)
                .filter(
                    Alert.user_id == user.id,
                    Alert.is_resolved == False,
                    Alert.alert_type.in_([
                        "Food Spoilage Alert",
                        "Expired / Remove Now",
                    ]),
                )
                .order_by(Alert.created_at.desc())
                .all()
            )

            grouped_food_items = []
            message_lines = []
            seen_food_ids = set()

            for alert in alerts:
                if not alert.food_item_id:
                    continue

                if alert.food_item_id in seen_food_ids:
                    continue

                food = db.query(FoodItem).filter(
                    FoodItem.id == alert.food_item_id,
                    FoodItem.user_id == user.id,
                ).first()

                if not food or food.is_used or food.is_discarded:
                    continue

                seen_food_ids.add(food.id)

                zone_name = food.zone.name if food.zone else "Fridge"
                expiry = (
                    food.expiry_date.strftime("%b %d, %Y")
                    if food.expiry_date else "Unknown"
                )
                status = food.freshness_status or alert.alert_type
                reason = alert.evidence_details or alert.message

                grouped_food_items.append({
                    "name": food.name,
                    "category": food.category or "Food",
                    "status": status,
                    "zone_name": zone_name,
                    "expiry_date": expiry,
                    "reason": reason,
                    "alert_type": alert.alert_type,
                    "item_type": getattr(food, "item_type", None),
                })

                message_lines.append(
                    f"- {food.name}: {status}; Location: {zone_name}; "
                    f"Expiry: {expiry}; Reason: {reason}"
                )

            if grouped_food_items:
                await notification.send(
                    user=user,
                    title=(
                        "Daily Spoilage Summary: "
                        f"{len(grouped_food_items)} item(s) need attention"
                    ),
                    message=(
                        "Here are the unresolved spoiled or expired foods "
                        "that still need attention today:\n"
                        + "\n".join(message_lines)
                    ),
                    channel="all",
                    metadata={
                        "alert_type": "Daily Spoilage Summary",
                        "food_items": grouped_food_items,
                    },
                    db=db,
                )

                logger.info(
                    "Daily spoilage summary processed for user %s: %s items",
                    user.id,
                    len(grouped_food_items),
                )

    except Exception as e:
        logger.error("Error in daily spoilage digest: %s", e)
    finally:
        db.close()

async def job_weekly_audit_reminder():
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            await notification.send(
                user=user,
                title="Weekly Fridge Audit Reminder 📸",
                message="It's Sunday! Take 2-5 photos of your fridge shelves to verify inventory and freshness.",
                channel="all",
                db=db
            )
    except Exception as e:
        logger.error(f"Error in weekly audit reminder job: {e}")
    finally:
        db.close()


def start_scheduler():
    # 1. Update sensors every 30 seconds
    scheduler.add_job(
        job_update_sensors,
        IntervalTrigger(seconds=30),
        id="sensor_sim",
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
    )

    # 2. Check for new alerts every minute
    scheduler.add_job(
        job_check_alerts,
        IntervalTrigger(minutes=1),
        id="minute_alerts",
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
    )

    # 3. Process repeating reminders every minute
    scheduler.add_job(
        job_process_repeating_alerts,
        IntervalTrigger(minutes=1),
        id="repeating_sms_alerts",
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
    )

    # 4. Existing daily email digest — 8 AM India time
    scheduler.add_job(
        job_daily_digest_8am,
        CronTrigger(
            hour=8,
            minute=0,
            timezone="Asia/Kolkata",
        ),
        id="daily_8am_digest",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
    )

    # 5. Grouped spoilage summary — 8 AM India time
    scheduler.add_job(
        job_daily_spoilage_digest,
        CronTrigger(
            hour=8,
            minute=0,
            timezone="Asia/Kolkata",
        ),
        id="daily_spoilage_digest",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
    )

    # 6. Weekly audit — Sunday at 10 AM India time
    scheduler.add_job(
        job_weekly_audit_reminder,
        CronTrigger(
            day_of_week="sun",
            hour=10,
            minute=0,
            timezone="Asia/Kolkata",
        ),
        id="weekly_audit",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
    )

    # Start the scheduler
    if not scheduler.running:
     scheduler.start()
     logger.info("APScheduler background jobs started successfully.")
def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")


