import logging
import asyncio
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from app.config import settings
from app.database import SessionLocal
from app.services.sensor_simulator import update_sensor_readings
from app.services.alert_engine import run_all_alert_rules, should_skip_quiet_hours
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
    Periodic job (running every 60s) that groups all due unresolved alerts
    for each user into ONE neat, readable summary notification (Email + Telegram)
    instead of spamming individual messages per food item.
    """
    if _sms_repeat_lock.locked():
        return

    async with _sms_repeat_lock:
        db = SessionLocal()
        try:
            now = datetime.utcnow()

            due_alerts = db.query(Alert).filter(
                Alert.is_resolved == False,
                Alert.status == "ACTIVE",
                Alert.next_reminder_at != None,
                Alert.next_reminder_at <= now,
            ).all()

            # Group due alerts by user_id
            alerts_by_user = {}
            for alert in due_alerts:
                if alert.user:
                    alerts_by_user.setdefault(alert.user_id, []).append(alert)

            for user_id, user_alerts in alerts_by_user.items():
                user = user_alerts[0].user
                if not user or not getattr(user, "spoilage_reminder_enabled", True):
                    for a in user_alerts:
                        a.next_reminder_at = None
                        a.next_sms_scheduled_at = None
                    db.commit()
                    continue

                # Respect user's quiet hours (e.g. 22:00 - 07:00)
                if should_skip_quiet_hours(user):
                    continue

                repeat_interval = (
                    getattr(user, "spoilage_reminder_interval_minutes", None)
                    or getattr(settings, "SMS_REMINDER_INTERVAL_MINUTES", 120)
                    or 120
                )

                summary_lines = []
                grouped_food_items = []
                seen_names = set()

                for alert in user_alerts:
                    food = alert.food_item
                    zone = alert.zone or (food.zone if food else None)
                    zone_name = zone.name if zone else "Fridge"
                    food_name = food.name if food else alert.title
                    status = food.freshness_status if food else alert.severity.capitalize()
                    expiry = (
                        food.expiry_date.strftime("%b %d")
                        if food and food.expiry_date
                        else "Check item"
                    )

                    if food_name not in seen_names:
                        seen_names.add(food_name)
                        summary_lines.append(
                            f"• {food_name} ({zone_name}) — {status} | {expiry}"
                        )
                        grouped_food_items.append({
                            "name": food_name,
                            "category": food.category if food else "Alert",
                            "status": status,
                            "zone_name": zone_name,
                            "expiry_date": expiry,
                            "reason": alert.evidence_details or alert.message,
                            "alert_type": alert.alert_type,
                        })

                    # Advance every bundled alert's next reminder together
                    alert.reminder_count = (alert.reminder_count or 1) + 1
                    alert.last_notification_at = now
                    alert.next_reminder_at = now + timedelta(minutes=repeat_interval)
                    alert.sms_repeat_count = alert.reminder_count
                    alert.last_sms_sent_at = now
                    alert.next_sms_scheduled_at = None

                if summary_lines:
                    count = len(summary_lines)
                    title = f"Smart Fridge Summary: {count} item(s) need attention"
                    message = (
                        f"Smart Fridge Summary ({count} items):\n\n"
                        + "\n".join(summary_lines)
                        + "\n\nOpen Smart Fridge AI to mark items used or remove spoiled food."
                    )

                    await notification.send(
                        user=user,
                        title=title,
                        message=message,
                        channel="all",
                        metadata={
                            "alert_type": "Grouped Fridge Summary",
                            "food_items": grouped_food_items,
                            "action_url": "/alerts",
                        },
                        db=db,
                    )
                    logger.info(
                        "Sent 1 grouped reminder summary (%s items) to user %s",
                        count,
                        user.email,
                    )

                db.commit()

            # Clear legacy per-item SMS schedules so they never fire individually
            legacy_alerts = db.query(Alert).filter(
                Alert.next_sms_scheduled_at != None,
                Alert.next_sms_scheduled_at <= now,
            ).all()
            if legacy_alerts:
                for a in legacy_alerts:
                    a.next_sms_scheduled_at = None
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
            if not (user.email_notifications_enabled or getattr(user, "sms_notifications_enabled", False)):
                continue

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
                if not alert.food_item_id or alert.food_item_id in seen_food_ids:
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
                    f"• {food.name} ({zone_name}) — {status} | Expiry: {expiry}"
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
                        "that still need attention today:\n\n"
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
            if not (user.email_notifications_enabled or getattr(user, "sms_notifications_enabled", False)):
                continue
            await notification.send(
                user=user,
                title="Weekly Fridge Audit Reminder",
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

    # 3. Process grouped repeating reminders every minute
    scheduler.add_job(
        job_process_repeating_alerts,
        IntervalTrigger(minutes=1),
        id="repeating_sms_alerts",
        replace_existing=True,
        misfire_grace_time=60,
        coalesce=True,
    )

    # 4. Daily email digest — 8 AM India time
    scheduler.add_job(
        job_daily_digest_8am,
        CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
        id="daily_8am_digest",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
    )

    # 5. Grouped spoilage summary — 8 AM India time
    scheduler.add_job(
        job_daily_spoilage_digest,
        CronTrigger(hour=8, minute=0, timezone="Asia/Kolkata"),
        id="daily_spoilage_digest",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
    )

    # 6. Weekly audit — Sunday at 10 AM India time
    scheduler.add_job(
        job_weekly_audit_reminder,
        CronTrigger(day_of_week="sun", hour=10, minute=0, timezone="Asia/Kolkata"),
        id="weekly_audit",
        replace_existing=True,
        misfire_grace_time=300,
        coalesce=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler background jobs started successfully.")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown()
        logger.info("APScheduler stopped.")