from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text
)
from sqlalchemy.orm import relationship
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="Smart Chef")
    phone_number = Column(String(50), nullable=True)
    
    # Notification Preferences & Channel Toggles
    email_notifications_enabled = Column(Boolean, default=True)
    push_notifications_enabled = Column(Boolean, default=True)
    sms_notifications_enabled = Column(Boolean, default=False)
    telegram_notifications_enabled = Column(Boolean, default=True)
    telegram_chat_id = Column(String(100), nullable=True)
    
    push_subscription = Column(Text, nullable=True)  # JSON string of PushSubscription object
    
    # Alert Category Toggles
    email_for_expiring = Column(Boolean, default=True)
    email_for_expired = Column(Boolean, default=True)
    email_daily_digest = Column(Boolean, default=True)
    push_for_expiring = Column(Boolean, default=True)
    push_for_expired = Column(Boolean, default=True)
    sms_for_critical = Column(Boolean, default=False)
    sms_for_expiring = Column(Boolean, default=False)
    sms_for_expired = Column(Boolean, default=True)
    sms_for_temperature = Column(Boolean, default=True)
    sms_for_dairy = Column(Boolean, default=True)
    sms_repeat_interval_minutes = Column(Integer, default=15)
    sms_max_duration_minutes = Column(Integer, default=120)

    # 2-Hour Spoilage Reminder Preferences
    spoilage_reminder_enabled = Column(Boolean, default=True)
    spoilage_reminder_interval_minutes = Column(Integer, default=120)  # Default 2 hours
    push_for_spoilage = Column(Boolean, default=True)

    alert_lead_days = Column(Integer, default=2)
    quiet_hours_start = Column(String(10), default="22:00")
    quiet_hours_end = Column(String(10), default="07:00")
    audit_day = Column(String(20), default="Sunday")
    audit_time = Column(String(10), default="10:00")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    foods = relationship("FoodItem", back_populates="user", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    audits = relationship("AuditSession", back_populates="user", cascade="all, delete-orphan")
    activities = relationship("ActivityHistory", back_populates="user", cascade="all, delete-orphan")
    notification_logs = relationship("NotificationLog", back_populates="user", cascade="all, delete-orphan")

    @property
    def sms_enabled(self) -> bool:
        return bool(self.sms_notifications_enabled) or bool(getattr(self, "telegram_notifications_enabled", False))

    @sms_enabled.setter
    def sms_enabled(self, val: bool):
        self.sms_notifications_enabled = bool(val)
        self.telegram_notifications_enabled = bool(val)


class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), unique=True, nullable=False)  # top_shelf, middle_shelf, bottom_shelf, vegetable_drawer, freezer
    target_temp_min = Column(Float, default=2.0)
    target_temp_max = Column(Float, default=5.0)
    target_humidity_min = Column(Float, default=60.0)
    target_humidity_max = Column(Float, default=80.0)
    current_temp = Column(Float, default=3.5)
    current_humidity = Column(Float, default=68.0)
    health_score = Column(Integer, default=95)
    status = Column(String(20), default="normal")  # normal, warning, critical
    description = Column(String(255), nullable=True)

    foods = relationship("FoodItem", back_populates="zone")
    sensor_readings = relationship("SensorReading", back_populates="zone", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="zone")


class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    category = Column(String(100), default="Packaged")
    item_type = Column(String(50), default="packaged")  # fruit, vegetable, packaged
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="pcs")
    added_at = Column(DateTime, default=datetime.utcnow)
    expiry_date = Column(DateTime, nullable=False)
    freshness_status = Column(String(50), default="Fresh")  # Fresh, Expiring Soon, Expired, Ripe, Overripe, Rotten
    barcode = Column(String(100), nullable=True)
    brand = Column(String(255), nullable=True)
    image_path = Column(String(500), nullable=True)
    source = Column(String(50), default="manual")  # fruit_scan, barcode_scan, manual
    is_used = Column(Boolean, default=False)
    is_discarded = Column(Boolean, default=False)
    estimated_cost = Column(Float, default=0.0)
    notes = Column(Text, nullable=True)

    user = relationship("User", back_populates="foods")
    zone = relationship("Zone", back_populates="foods")
    images = relationship("FoodImage", back_populates="food_item", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="food_item")


class FoodImage(Base):
    __tablename__ = "food_images"

    id = Column(Integer, primary_key=True, index=True)
    food_item_id = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    path = Column(String(500), nullable=False)
    predicted_label = Column(String(100), nullable=True)
    predicted_freshness = Column(String(50), nullable=True)
    confidence = Column(Float, default=0.0)
    verified_label = Column(String(100), nullable=True)
    verified_freshness = Column(String(50), nullable=True)
    split = Column(String(50), default="pending")  # train, val, test, pending
    created_at = Column(DateTime, default=datetime.utcnow)

    food_item = relationship("FoodItem", back_populates="images")


class BarcodeCache(Base):
    __tablename__ = "barcode_cache"

    id = Column(Integer, primary_key=True, index=True)
    barcode = Column(String(100), unique=True, index=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    brand = Column(String(255), nullable=True)
    category = Column(String(100), nullable=True)
    image_url = Column(String(500), nullable=True)
    quantity_str = Column(String(100), nullable=True)
    nutri_score = Column(String(20), nullable=True)
    raw_data = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    food_item_id = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=True)
    alert_type = Column(String(100), nullable=False)  # Expiring Soon, Expired / Remove Now, Item Not Seen, Low-confidence Prediction, Compatibility Warning, Temperature Warning
    severity = Column(String(20), default="warning")  # info, warning, critical
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    is_resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="ACTIVE")  # ACTIVE, REMOVED, RESOLVED
    confidence_score = Column(Float, nullable=True)
    last_notification_at = Column(DateTime, nullable=True)
    next_reminder_at = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)
    action_recommended = Column(String(255), default="Remove or inspect this food item")
    channel_sent = Column(String(50), default="in_app")  # email, web_push, sms, in_app
    first_sms_sent_at = Column(DateTime, nullable=True)
    last_sms_sent_at = Column(DateTime, nullable=True)
    next_sms_scheduled_at = Column(DateTime, nullable=True)
    sms_repeat_count = Column(Integer, default=0)
    evidence_type = Column(String(50), default="freshness_assessment", nullable=True)  # ml_model, expiration_date, audit_session, threshold
    evidence_details = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="alerts")
    food_item = relationship("FoodItem", back_populates="alerts")
    zone = relationship("Zone", back_populates="alerts")
    notification_logs = relationship("NotificationLog", back_populates="alert", cascade="all, delete-orphan")


class NotificationLog(Base):
    __tablename__ = "notifications_log"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=True)
    food_name = Column(String(255), nullable=True)
    provider_message_id = Column(String(100), nullable=True)
    repeat_count = Column(Integer, default=1)
    channel = Column(String(50), nullable=False)  # email, web_push, sms
    provider = Column(String(50), nullable=True)  # smtp, resend, brevo, vapid, twilio, fast2sms
    recipient = Column(String(255), nullable=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    status = Column(String(50), default="sent")  # pending, accepted, delivered, simulated, failed
    error_message = Column(Text, nullable=True)
    attempts = Column(Integer, default=1)
    metadata_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    sent_at = Column(DateTime, nullable=True)
    next_reminder_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="notification_logs")
    alert = relationship("Alert", back_populates="notification_logs")


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    temperature = Column(Float, nullable=False)
    humidity = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    zone = relationship("Zone", back_populates="sensor_readings")


class AuditSession(Base):
    __tablename__ = "audit_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(50), default="completed")  # completed, pending_review
    total_detected = Column(Integer, default=0)
    matched_count = Column(Integer, default=0)
    missing_count = Column(Integer, default=0)
    unknown_count = Column(Integer, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="audits")
    results = relationship("AuditResult", back_populates="audit_session", cascade="all, delete-orphan")


class AuditResult(Base):
    __tablename__ = "audit_results"

    id = Column(Integer, primary_key=True, index=True)
    audit_session_id = Column(Integer, ForeignKey("audit_sessions.id"), nullable=False)
    food_item_id = Column(Integer, ForeignKey("food_items.id"), nullable=True)
    detected_name = Column(String(255), nullable=True)
    detected_freshness = Column(String(50), nullable=True)
    image_path = Column(String(500), nullable=True)
    status = Column(String(50), default="matched")  # matched, missing, unknown
    resolution = Column(String(50), nullable=True)  # still_here, marked_used, removed

    audit_session = relationship("AuditSession", back_populates="results")
    food_item = relationship("FoodItem")


class ShelfLifeDefault(Base):
    __tablename__ = "shelf_life_defaults"

    id = Column(Integer, primary_key=True, index=True)
    item_name = Column(String(100), unique=True, nullable=False)
    category = Column(String(100), nullable=False)
    typical_shelf_life_days = Column(Integer, nullable=False)
    recommended_zone_code = Column(String(50), default="middle_shelf")
    is_ethylene_producer = Column(Boolean, default=False)
    is_ethylene_sensitive = Column(Boolean, default=False)


class ActivityHistory(Base):
    __tablename__ = "activity_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    action = Column(String(50), nullable=False)  # added, used, discarded, expired, updated
    food_item_name = Column(String(255), nullable=False)
    quantity = Column(Float, default=1.0)
    unit = Column(String(50), default="pcs")
    estimated_cost = Column(Float, default=0.0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    user = relationship("User", back_populates="activities")
