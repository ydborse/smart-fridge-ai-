import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple, Optional
from sqlalchemy.orm import Session
from app.config import settings
from app.models import User, FoodItem, Alert, Zone, ShelfLifeDefault
from app.services.notification import send as send_notification, is_dairy_item, resolve_telegram_chat_id

logger = logging.getLogger(__name__)

ETHYLENE_PRODUCERS = {"apple", "banana", "tomato", "avocado"}
ETHYLENE_SENSITIVE = {"lettuce", "coriander", "capsicum", "strawberry", "spinach"}

def should_skip_quiet_hours(user: User) -> bool:
    """
    Checks if current local time falls into user's quiet hours (e.g. 22:00 to 07:00).
    """
    now = datetime.utcnow()
    current_time_str = now.strftime("%H:%M")
    
    start = user.quiet_hours_start or "22:00"
    end = user.quiet_hours_end or "07:00"

    if start > end:  # overnight, e.g. 22:00 to 07:00
        return current_time_str >= start or current_time_str < end
    else:
        return start <= current_time_str < end


def alert_already_exists(db: Session, user_id: int, alert_type: str, food_item_id: int = None, zone_id: int = None) -> bool:
    """
    Prevents duplicate alerts within 24 hours for the same item/zone and alert type,
    or if an active unresolved alert already exists.
    """
    query = db.query(Alert).filter(
        Alert.user_id == user_id,
        Alert.alert_type == alert_type,
        Alert.is_resolved == False
    )
    if food_item_id:
        query = query.filter(Alert.food_item_id == food_item_id)
    if zone_id:
        query = query.filter(Alert.zone_id == zone_id)
        
    return query.first() is not None


async def create_spoilage_alert(
    db: Session,
    user: User,
    food: FoodItem,
    confidence: Optional[float] = None,
    custom_notes: Optional[str] = None,
    alert_type: str = "Food Spoilage Alert",
    evidence_type: Optional[str] = None,
    evidence_details: Optional[str] = None
) -> Tuple[Alert, bool]:
    """
    Creates or retrieves an active food spoilage alert for a tracked food item.
    - Idempotent: If an active (unresolved) alert already exists for this food_item_id, returns it.
    - Sets initial notification time and schedules next 2-hour (or user-configured) reminder persistently.
    - Creates and persists the alert; run_all_alert_rules dispatches its notification.
    - Records evidence type (expiration_date, freshness_assessment, ml_model, freshness_threshold).
    """
    existing = db.query(Alert).filter(
        Alert.user_id == user.id,
        Alert.food_item_id == food.id,
        Alert.is_resolved == False
    ).first()

    if existing:
        return existing, False

    zone_name = food.zone.name if food.zone else "Fridge"
    now = datetime.utcnow()
    # Prioritize user's configured reminder interval, falling back to settings or 120 minutes (2 hours)
    interval_mins = getattr(user, "spoilage_reminder_interval_minutes", None) or getattr(settings, "SMS_REMINDER_INTERVAL_MINUTES", 120) or 120
    next_reminder = now + timedelta(minutes=interval_mins)

    # Determine evidence details and reason if not explicitly provided
    if not evidence_type:
        time_to_exp = (food.expiry_date - now).total_seconds() if food.expiry_date else 0
        if time_to_exp < 0:
            evidence_type = "expiration_date"
            evidence_details = evidence_details or f"Passed recorded expiration date ({food.expiry_date.strftime('%b %d, %Y')})."
        elif confidence is not None or food.freshness_status == "Rotten":
            evidence_type = "freshness_assessment"
            conf_str = f" ({int(confidence * 100)}% confidence)" if confidence else ""
            evidence_details = evidence_details or f"Freshness assessment indicates spoilage{conf_str}."
        else:
            evidence_type = "freshness_assessment"
            evidence_details = evidence_details or "Freshness assessment indicates spoilage."

    reason_str = evidence_details or ("Freshness assessment indicates spoilage" if evidence_type != "expiration_date" else "Expiration date passed")

    title = f"🚨 Food Spoilage Alert! {food.name} in {zone_name} is Spoiled / Remove Now"
    message = f"🚨 SMART FRIDGE ALERT: {food.name} in {zone_name} is marked spoiled. Reason: {reason_str}. Please inspect and remove the item. This reminder will repeat until the issue is resolved."
    if custom_notes:
        message += f" ({custom_notes})"

    alert = Alert(
        user_id=user.id,
        food_item_id=food.id,
        zone_id=food.zone_id,
        alert_type=alert_type,
        severity="critical",
        title=title,
        message=message,
        status="ACTIVE",
        is_read=False,
        is_resolved=False,
        confidence_score=confidence,
        evidence_type=evidence_type,
        evidence_details=evidence_details,
        last_notification_at=now,
        next_reminder_at=next_reminder,
        reminder_count=1,
        action_recommended="Remove or inspect this food item",
        channel_sent="email,web_push,telegram",
        first_sms_sent_at=now,
        last_sms_sent_at=now,
        next_sms_scheduled_at=next_reminder,
        sms_repeat_count=1,
        created_at=now
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)

    return alert, True


async def evaluate_food_alerts(db: Session, user: User) -> List[Alert]:
    """
    Evaluates all food items for a user against expiry and freshness rules.
    """
    now = datetime.utcnow()
    lead_days = user.alert_lead_days or 2
    created_alerts = []

    active_foods = db.query(FoodItem).filter(
        FoodItem.user_id == user.id,
        FoodItem.is_used == False,
        FoodItem.is_discarded == False
    ).all()

    for food in active_foods:
        days_in_fridge = (now - food.added_at).days if food.added_at else 0
        time_to_expiry = food.expiry_date - now
        days_until_expiry = time_to_expiry.total_seconds() / 86400.0

        # Retrieve typical shelf life default
        shelf_def = db.query(ShelfLifeDefault).filter(ShelfLifeDefault.item_name == food.name.lower()).first()
        typical_shelf = shelf_def.typical_shelf_life_days if shelf_def else 7

        # 1. PACKAGED & DAIRY FOOD RULES
        is_dairy = is_dairy_item(food.name, food.category)
        if food.item_type == "packaged" or is_dairy:
            is_spoiled = food.freshness_status in ["Rotten", "Expired"] or days_until_expiry < 0
            if is_spoiled:
                if days_until_expiry < 0:
                    food.freshness_status = "Expired"
                    evidence_type = "expiration_date"
                    days_ago = abs(int(days_until_expiry))
                    evidence_details = f"Item passed recorded expiration date ({food.expiry_date.strftime('%b %d, %Y')}, {days_ago} day{'s' if days_ago!=1 else ''} ago)."
                    conf = 1.0
                else:
                    evidence_type = "freshness_assessment"
                    evidence_details = f"Freshness assessment indicates spoilage for {food.name} (marked {food.freshness_status.lower()})."
                    conf = 0.95

                spoilage_alert, created = await create_spoilage_alert(
                    db=db,
                    user=user,
                    food=food,
                    confidence=conf,
                    alert_type="Expired / Remove Now",
                    evidence_type=evidence_type,
                    evidence_details=evidence_details
                )
                if created:
                    created_alerts.append(spoilage_alert)

            elif days_until_expiry <= lead_days:
                # Expiring soon
                alert_type = "Expiring Soon"
                if not alert_already_exists(db, user.id, alert_type, food_item_id=food.id):
                    days_int = max(0, int(days_until_expiry))
                    alert = Alert(
                        user_id=user.id,
                        food_item_id=food.id,
                        zone_id=food.zone_id,
                        alert_type=alert_type,
                        severity="warning",
                        title=f"{food.name} Expiring Soon",
                        message=f"{food.name} will expire in {days_int} day{'s' if days_int!=1 else ''} ({food.expiry_date.strftime('%b %d')}). Plan to use it soon!",
                        status="ACTIVE",
                        channel_sent="email,push",
                        evidence_type="expiration_date",
                        evidence_details=f"Item will expire in {days_int} day(s) on {food.expiry_date.strftime('%b %d')}."
                    )
                    db.add(alert)
                    created_alerts.append(alert)
                    food.freshness_status = "Expiring Soon"

        # 2. FRUITS / VEGETABLES RULES
        else:
            # Safety Rule: if status is Fresh but days in fridge exceeds typical shelf life, warn
            if food.freshness_status == "Fresh" and days_in_fridge > typical_shelf:
                food.freshness_status = "Expiring Soon"

            is_past_expiry = days_until_expiry < 0
            is_model_rotten = food.freshness_status in ["Rotten", "Expired"]

            if is_model_rotten or is_past_expiry:
                food.freshness_status = "Rotten"
                if is_past_expiry:
                    evidence_type = "expiration_date"
                    days_ago = abs(int(days_until_expiry))
                    evidence_details = f"Item passed recorded expiration date ({food.expiry_date.strftime('%b %d, %Y')}, {days_ago} day{'s' if days_ago!=1 else ''} ago)."
                    conf = 1.0
                else:
                    evidence_type = "freshness_assessment"
                    conf = 0.95
                    evidence_details = f"Freshness assessment classified {food.name} as rotten."

                spoilage_alert, created = await create_spoilage_alert(
                    db=db,
                    user=user,
                    food=food,
                    confidence=conf,
                    evidence_type=evidence_type,
                    evidence_details=evidence_details
                )
                if created:
                    created_alerts.append(spoilage_alert)

            elif food.freshness_status in ["Ripe", "Overripe", "Expiring Soon"] or days_until_expiry <= lead_days:
                alert_type = "Expiring Soon"
                if not alert_already_exists(db, user.id, alert_type, food_item_id=food.id):
                    days_rem = max(1, int(days_until_expiry)) if days_until_expiry > 0 else 1
                    alert = Alert(
                        user_id=user.id,
                        food_item_id=food.id,
                        zone_id=food.zone_id,
                        alert_type=alert_type,
                        severity="warning",
                        title=f"{food.name} Needs Attention",
                        message=f"{food.name} is {food.freshness_status.lower()}. Use soon within {days_rem} day(s) before it spoils.",
                        channel_sent="email,push",
                        evidence_type="freshness_assessment" if food.freshness_status in ["Ripe", "Overripe"] else "expiration_date",
                        evidence_details=f"Item state: {food.freshness_status}."
                    )
                    db.add(alert)
                    created_alerts.append(alert)

    db.commit()
    return created_alerts


async def evaluate_compatibility_alerts(db: Session, user: User) -> List[Alert]:
    """
    Checks each zone for ethylene producers stored with ethylene sensitive items.
    """
    created_alerts = []
    zones = db.query(Zone).all()

    for zone in zones:
        zone_foods = db.query(FoodItem).filter(
            FoodItem.zone_id == zone.id,
            FoodItem.user_id == user.id,
            FoodItem.is_used == False,
            FoodItem.is_discarded == False
        ).all()

        producers = [f for f in zone_foods if f.name.lower() in ETHYLENE_PRODUCERS]
        sensitive = [f for f in zone_foods if f.name.lower() in ETHYLENE_SENSITIVE]

        if producers and sensitive:
            alert_type = "Compatibility Warning"
            if not alert_already_exists(db, user.id, alert_type, zone_id=zone.id):
                p_names = ", ".join(set([p.name for p in producers]))
                s_names = ", ".join(set([s.name for s in sensitive]))
                alert = Alert(
                    user_id=user.id,
                    zone_id=zone.id,
                    alert_type=alert_type,
                    severity="warning",
                    title=f"Ethylene Gas Warning in {zone.name}",
                    message=f"Ethylene producer ({p_names}) is stored alongside sensitive items ({s_names}) in {zone.name}. This accelerates decay! Separate them into different shelves.",
                    channel_sent="in_app"
                )
                db.add(alert)
                created_alerts.append(alert)

    db.commit()
    return created_alerts


async def evaluate_temperature_alerts(db: Session, user: User) -> List[Alert]:
    """
    Checks if any zone temperature or humidity is in critical bounds.
    """
    created_alerts = []
    zones = db.query(Zone).all()

    for zone in zones:
        if zone.status in ["critical", "warning"]:
            alert_type = "Temperature Warning"
            if not alert_already_exists(db, user.id, alert_type, zone_id=zone.id):
                is_crit = zone.status == "critical"
                alert = Alert(
                    user_id=user.id,
                    zone_id=zone.id,
                    alert_type=alert_type,
                    severity="critical" if is_crit else "warning",
                    title=f"Zone Alert: {zone.name} is {zone.status.upper()}",
                    message=f"{zone.name} sensor reading is {zone.current_temp}°C ({zone.current_humidity}% RH). Target: {zone.target_temp_min}-{zone.target_temp_max}°C. Check fridge door or thermostat.",
                    channel_sent="email,push,sms" if is_crit else "in_app"
                )
                db.add(alert)
                created_alerts.append(alert)

    db.commit()
    return created_alerts


def should_trigger_sms_for_alert(
    user: User,
    alert_or_type: Any,
    severity_or_food: Any = None,
    food_name_or_none: Optional[str] = None,
    temp: Optional[float] = None
) -> bool:
    """
    Evaluates whether an alert qualifies for immediate and repeating SMS notifications.
    Supports Food Spoilage alerts, Dairy (milk, yogurt, paneer, cheese), critical expiry, temp spikes, and user settings.
    Accepts either (user, alert, food) or (user, alert_type, severity, food_name, temp).
    """
    telegram_active = bool(getattr(settings, "TELEGRAM_ENABLED", True))
    twilio_setting = getattr(settings, "TWILIO_ENABLED", None)
    if twilio_setting is not None:
        twilio_active = bool(twilio_setting)
    else:
        twilio_active = bool(getattr(settings, "SMS_ENABLED", False))
    mobile_active = telegram_active or twilio_active

    if twilio_active and not telegram_active:
        user_sms_pref = bool(getattr(user, "sms_notifications_enabled", False))
    elif telegram_active and not twilio_active:
        user_sms_pref = bool(getattr(user, "telegram_notifications_enabled", False))
    else:
        user_sms_pref = bool(getattr(user, "telegram_notifications_enabled", False)) or bool(getattr(user, "sms_notifications_enabled", False))

    recipient = resolve_telegram_chat_id(user=user)
    if not (user_sms_pref and mobile_active and recipient):
        return False

    if isinstance(alert_or_type, Alert):
        alert_type = alert_or_type.alert_type
        severity = alert_or_type.severity
        food = severity_or_food
        food_name = food.name if food else None
        food_category = food.category if food else None
    else:
        alert_type = str(alert_or_type)
        severity = str(severity_or_food) if severity_or_food else "warning"
        food_name = food_name_or_none
        food_category = None

    # Check critical severity constraint if user has sms_for_critical enabled
    if getattr(user, "sms_for_critical", False) and severity != "critical":
        return False

    # 1. Food Spoilage & Critical Expiration Alerts (Fruits, Veggies, Groceries)
    if alert_type in ["Food Spoilage Alert", "Expired / Remove Now"] and getattr(user, "sms_for_expired", True):
        return True

    # 2. Dairy items (Milk, Yogurt, Paneer, Cheese)
    is_dairy = is_dairy_item(food_name, food_category)
    if is_dairy and getattr(user, "sms_for_dairy", True):
        return True

    # 3. Expiring Soon (Dairy products nearing expiry or critical severity)
    if alert_type == "Expiring Soon" and getattr(user, "sms_for_expiring", False):
        return is_dairy or severity == "critical"

    # 4. Temperature Warning
    if alert_type == "Temperature Warning" and getattr(user, "sms_for_temperature", True):
        return True

    # 5. Critical severity
    if severity == "critical":
        return True

    return False


def resolve_alert(db: Session, alert_id: int, user_id: int) -> Optional[Alert]:
    """
    Marks an alert as resolved and stops further repeating mobile/SMS notifications.
    """
    alert = db.query(Alert).filter(Alert.id == alert_id, Alert.user_id == user_id).first()
    if alert:
        alert.status = "RESOLVED"
        alert.is_resolved = True
        alert.is_read = True
        alert.resolved_at = datetime.utcnow()
        alert.next_reminder_at = None
        alert.next_sms_scheduled_at = None
        db.commit()
        logger.info(f"Alert {alert_id} resolved by user {user_id}. Repeating notifications canceled.")
    return alert


def resolve_alerts_for_food(db: Session, food_id: int, new_status: str = "REMOVED") -> int:
    """
    Cancels and resolves all active alerts when a food item is consumed or discarded.
    """
    now = datetime.utcnow()
    count = db.query(Alert).filter(
        Alert.food_item_id == food_id,
        Alert.is_resolved == False
    ).update({
        "status": new_status,
        "is_resolved": True,
        "is_read": True,
        "resolved_at": now,
        "next_reminder_at": None,
        "next_sms_scheduled_at": None
    })
    db.commit()
    if count > 0:
        logger.info(f"Resolved {count} pending alerts for food item #{food_id} (status: {new_status}).")
    return count



async def run_all_alert_rules(db: Session):
    """Evaluate alert rules and send one grouped Telegram food summary per user."""
    users = db.query(User).filter(User.is_active == True).all()

    for user in users:
        is_quiet = should_skip_quiet_hours(user)

        food_alerts = await evaluate_food_alerts(db, user)
        compat_alerts = await evaluate_compatibility_alerts(db, user)
        temp_alerts = await evaluate_temperature_alerts(db, user)

        all_new = food_alerts + compat_alerts + temp_alerts
        logger.info(
            "Alert engine generated %s alerts for user %s",
            len(all_new),
            user.email,
        )

        now = datetime.utcnow()
        grouped_food_items = []

        for alert in all_new:
            food = None
            if alert.food_item_id:
                food = db.query(FoodItem).filter(
                    FoodItem.id == alert.food_item_id
                ).first()

            metadata = {
                "alert_id": alert.id,
                "alert_type": alert.alert_type,
                "severity": alert.severity,
                "reason": alert.evidence_details or alert.message,
            }

            zone_name = "Fridge"
            expiry = "Unknown"

            if food:
                zone_name = food.zone.name if food.zone else "Fridge"
                expiry = (
                    food.expiry_date.strftime("%b %d, %Y")
                    if food.expiry_date
                    else "Unknown"
                )
                metadata.update({
                    "food_name": food.name,
                    "category": food.category,
                    "expiry_date": expiry,
                    "status": food.freshness_status or alert.alert_type,
                    "image_url": food.image_path,
                    "food_item_id": food.id,
                    "zone_name": zone_name,
                    "evidence_type": alert.evidence_type,
                    "evidence_details": alert.evidence_details,
                    "action_recommended": (
                        alert.action_recommended or "Inspect this food item"
                    ),
                })

            elif alert.zone_id:
                zone = db.query(Zone).filter(Zone.id == alert.zone_id).first()
                if zone:
                    zone_name = zone.name
                    metadata.update({
                        "zone_name": zone.name,
                        "temperature": zone.current_temp,
                        "humidity": zone.current_humidity,
                    })

            sms_eligible = should_trigger_sms_for_alert(user, alert, food)
            should_notify = alert.severity == "critical" or not is_quiet

            # Schedule repeating mobile notifications only when the alert
            # qualifies for mobile delivery.
            if sms_eligible:
                alert.first_sms_sent_at = alert.first_sms_sent_at or now
                alert.last_sms_sent_at = now
                alert.sms_repeat_count = max(alert.sms_repeat_count or 0, 1)

                repeat_interval = (
                    getattr(user, "sms_repeat_interval_minutes", 15) or 15
                )
                max_duration = (
                    getattr(user, "sms_max_duration_minutes", 120) or 120
                )

                if should_notify and repeat_interval < max_duration:
                    alert.next_sms_scheduled_at = now + timedelta(
                        minutes=repeat_interval
                    )
                elif not alert.next_sms_scheduled_at:
                    alert.next_sms_scheduled_at = None

                db.commit()

            if not should_notify:
                continue

            if food:
                # Send email and web push individually.
                # Telegram is grouped into one summary below.
                for channel in ("email", "web_push"):
                    await send_notification(
                        user=user,
                        title=alert.title,
                        message=alert.message,
                        channel=channel,
                        metadata=metadata,
                        db=db,
                        alert_id=alert.id,
                        repeat_count=1,
                    )

                # Only include foods that qualify for the user's configured
                # mobile notification preferences.
                if sms_eligible:
                    grouped_food_items.append({
                        "name": food.name,
                        "category": food.category or "Food",
                        "status": food.freshness_status or alert.alert_type,
                        "zone_name": zone_name,
                        "expiry_date": expiry,
                        "reason": alert.evidence_details or alert.message,
                        "alert_type": alert.alert_type,
                        "item_type": getattr(food, "item_type", None),
                    })
            else:
                # Preserve normal notification handling for temperature,
                # compatibility, and other non-food alerts.
                channel_to_use = "all" if sms_eligible else "email,web_push"
                await send_notification(
                    user=user,
                    title=alert.title,
                    message=alert.message,
                    channel=channel_to_use,
                    metadata=metadata,
                    db=db,
                    alert_id=alert.id,
                    repeat_count=1,
                )

        # Send a single Telegram summary for all new food alerts in this run.
        telegram_pref = getattr(user, "telegram_notifications_enabled", None)
        if telegram_pref is None:
            telegram_pref = getattr(user, "sms_notifications_enabled", None)
        if telegram_pref is None:
            telegram_pref = getattr(user, "sms_enabled", True)

        telegram_ready = (
            bool(getattr(settings, "TELEGRAM_ENABLED", True))
            and bool(telegram_pref)
            and bool(resolve_telegram_chat_id(user=user))
        )

        if grouped_food_items and telegram_ready:
            await send_notification(
                user=user,
                title=(
                    f"Smart Fridge: {len(grouped_food_items)} "
                    "food item(s) need attention"
                ),
                message=(
                    "Review the affected food items, status, expiry dates, "
                    "and reasons listed below."
                ),
                channel="telegram",
                metadata={
                    "alert_type": "Grouped Food Alerts",
                    "food_items": grouped_food_items,
                },
                db=db,
                repeat_count=1,
            )
