from datetime import datetime
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, EmailStr

# Auth Schemas
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = "Smart Chef"
    phone_number: Optional[str] = None

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    phone_number: Optional[str] = None
    email_notifications_enabled: bool = True
    push_notifications_enabled: bool = True
    sms_notifications_enabled: bool = False
    sms_enabled: bool = False
    telegram_notifications_enabled: bool = True
    telegram_chat_id: Optional[str] = None
    push_subscription: Optional[str] = None
    email_for_expiring: bool = True
    email_for_expired: bool = True
    email_daily_digest: bool = True
    push_for_expiring: bool = True
    push_for_expired: bool = True
    push_for_temperature: bool = True
    sms_for_critical: bool = False
    sms_for_expiring: bool = False
    sms_for_expired: bool = True
    sms_for_temperature: bool = True
    sms_for_dairy: bool = True
    sms_repeat_interval_minutes: int = 15
    sms_max_duration_minutes: int = 120
    spoilage_reminder_enabled: bool = True
    spoilage_reminder_interval_minutes: int = 120
    push_for_spoilage: bool = True
    alert_lead_days: int = 2
    quiet_hours_start: str = "22:00"
    quiet_hours_end: str = "07:00"
    audit_day: str = "Sunday"
    audit_time: str = "10:00"

    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email_notifications_enabled: Optional[bool] = None
    push_notifications_enabled: Optional[bool] = None
    sms_notifications_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    telegram_notifications_enabled: Optional[bool] = None
    telegram_chat_id: Optional[str] = None
    push_subscription: Optional[str] = None
    email_for_expiring: Optional[bool] = None
    email_for_expired: Optional[bool] = None
    email_daily_digest: Optional[bool] = None
    push_for_expiring: Optional[bool] = None
    push_for_expired: Optional[bool] = None
    push_for_temperature: Optional[bool] = None
    sms_for_critical: Optional[bool] = None
    sms_for_expiring: Optional[bool] = None
    sms_for_expired: Optional[bool] = None
    sms_for_temperature: Optional[bool] = None
    sms_for_dairy: Optional[bool] = None
    sms_repeat_interval_minutes: Optional[int] = None
    sms_max_duration_minutes: Optional[int] = None
    spoilage_reminder_enabled: Optional[bool] = None
    spoilage_reminder_interval_minutes: Optional[int] = None
    push_for_spoilage: Optional[bool] = None
    alert_lead_days: Optional[int] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    audit_day: Optional[str] = None
    audit_time: Optional[str] = None


# Zone Schemas
class ZoneBase(BaseModel):
    name: str
    code: str
    target_temp_min: float
    target_temp_max: float
    target_humidity_min: float
    target_humidity_max: float
    current_temp: float
    current_humidity: float
    health_score: int
    status: str
    description: Optional[str] = None

class ZoneOut(ZoneBase):
    id: int
    item_count: Optional[int] = 0

    class Config:
        from_attributes = True

# Food Schemas
class FoodItemCreate(BaseModel):
    name: str
    category: str = "Packaged"
    item_type: str = "packaged"  # fruit, vegetable, packaged
    zone_id: int
    quantity: float = 1.0
    unit: str = "pcs"
    expiry_date: datetime
    freshness_status: str = "Fresh"
    barcode: Optional[str] = None
    brand: Optional[str] = None
    image_path: Optional[str] = None
    source: str = "manual"  # fruit_scan, barcode_scan, manual
    estimated_cost: Optional[float] = 0.0
    notes: Optional[str] = None

class FoodItemUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    item_type: Optional[str] = None
    zone_id: Optional[int] = None
    quantity: Optional[float] = None
    unit: Optional[str] = None
    expiry_date: Optional[datetime] = None
    freshness_status: Optional[str] = None
    notes: Optional[str] = None

class FoodItemOut(BaseModel):
    id: int
    user_id: int
    name: str
    category: str
    item_type: str
    zone_id: int
    zone_name: Optional[str] = None
    zone_code: Optional[str] = None
    quantity: float
    unit: str
    added_at: datetime
    expiry_date: datetime
    freshness_status: str
    barcode: Optional[str] = None
    brand: Optional[str] = None
    image_path: Optional[str] = None
    source: str
    is_used: bool
    is_discarded: bool
    estimated_cost: float
    notes: Optional[str] = None
    days_until_expiry: Optional[int] = None

    class Config:
        from_attributes = True

# Prediction Schemas
class PredictionItem(BaseModel):
    item_name: str
    freshness_class: str  # Fresh, Ripe, Overripe, Rotten (or for dairy: Fresh, Expiring Soon, Expired, Uncertain)
    confidence: float
    typical_shelf_life_days: int
    suggested_expiry_date: datetime
    suggested_zone_id: int
    suggested_zone_name: str
    category: str
    item_type: str
    needs_manual_check: bool = False
    freshness_confidence: Optional[float] = None
    condition_notes: Optional[str] = None
    is_dairy: Optional[bool] = False
    is_unknown: Optional[bool] = False
    brand: Optional[str] = None
    extracted_date: Optional[str] = None
    date_type: Optional[str] = None
    date_status: Optional[str] = None
    ocr_confidence: Optional[float] = None
    is_estimated: Optional[bool] = False
    detected_text: Optional[str] = None

class PredictionResponse(BaseModel):
    top_prediction: PredictionItem
    all_predictions: List[PredictionItem]
    image_url: str
    disclaimer: str = "Freshness predictions are assistive and not a food safety guarantee."

# Barcode Schemas
class BarcodeProductOut(BaseModel):
    barcode: str
    name: str
    brand: Optional[str] = None
    category: str = "Packaged"
    image_url: Optional[str] = None
    quantity_str: Optional[str] = None
    nutri_score: Optional[str] = None
    default_shelf_life_days: int = 7
    suggested_expiry_date: datetime
    suggested_zone_id: int
    suggested_zone_name: str

# Sensor Schemas
class SensorReadingIn(BaseModel):
    zone_code: str
    temperature: float
    humidity: float

class SensorReadingOut(BaseModel):
    id: int
    zone_id: int
    zone_name: str
    temperature: float
    humidity: float
    timestamp: datetime

    class Config:
        from_attributes = True

# Alert Schemas
class AlertOut(BaseModel):
    id: int
    food_item_id: Optional[int] = None
    food_item_name: Optional[str] = None
    food_category: Optional[str] = None
    food_freshness: Optional[str] = None
    food_image: Optional[str] = None
    zone_id: Optional[int] = None
    zone_name: Optional[str] = None
    alert_type: str
    severity: str
    title: str
    message: str
    status: str = "ACTIVE"
    is_read: bool
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    confidence_score: Optional[float] = None
    last_notification_at: Optional[datetime] = None
    next_reminder_at: Optional[datetime] = None
    reminder_count: int = 0
    action_recommended: Optional[str] = "Remove or inspect this food item"
    first_sms_sent_at: Optional[datetime] = None
    last_sms_sent_at: Optional[datetime] = None
    next_sms_scheduled_at: Optional[datetime] = None
    sms_repeat_count: int = 0
    channel_sent: Optional[str] = None
    evidence_type: Optional[str] = "freshness_assessment"
    evidence_details: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class SpoilageAlertRequest(BaseModel):
    food_item_id: int
    custom_notes: Optional[str] = None

# Dashboard Summary Schema
class StatOverview(BaseModel):
    total_items: int
    fresh_items: int
    expiring_soon_items: int
    expired_items: int

class DashboardSummaryOut(BaseModel):
    stats: StatOverview
    insights: List[str]
    expiring_soon: List[FoodItemOut]
    recently_added: List[FoodItemOut]
    zone_stats: List[Any]
    temperature_history_24h: List[Any]
    unread_alerts_count: int

# Audit Schemas
class AuditSessionOut(BaseModel):
    id: int
    status: str
    total_detected: int
    matched_count: int
    missing_count: int
    unknown_count: int
    notes: Optional[str] = None
    created_at: datetime
    results: List[Any]

class AuditMissingResolve(BaseModel):
    result_id: int
    resolution: str  # still_here, marked_used, removed

# Dataset / Retraining Schemas
class FeedbackCreate(BaseModel):
    food_image_id: Optional[int] = None
    correct_item_name: str
    correct_freshness: str
    image_path: Optional[str] = None

class DatasetStatsOut(BaseModel):
    total_images: int
    splits: dict
    classes: dict
    pending_count: int
    items: List[str]

# Notification Schemas
class PushSubscriptionPayload(BaseModel):
    endpoint: str
    keys: dict

class NotificationLogOut(BaseModel):
    id: int
    user_id: int
    alert_id: Optional[int] = None
    food_name: Optional[str] = None
    provider_message_id: Optional[str] = None
    repeat_count: int = 1
    channel: str
    provider: Optional[str] = None
    recipient: Optional[str] = None
    title: str
    message: str
    status: str
    error_message: Optional[str] = None
    attempts: int
    created_at: datetime
    sent_at: Optional[datetime] = None
    next_reminder_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class NotificationTestRequest(BaseModel):
    channel: str  # email, web_push, sms
    recipient: Optional[str] = None
    message: Optional[str] = None

# Dairy Packaging Recognition Schema
class DairyPredictionResponse(BaseModel):
    category: str
    display_name: str
    confidence: float
    all_scores: Dict[str, float]
    suggested_shelf: str
    suggested_zone_id: int
    suggested_zone_code: str
    typical_shelf_life_days: int
    suggested_expiry_date: str
    storage_tips: str
    user_guidance: Optional[str] = None
    needs_manual_check: bool
    is_dairy: bool = True
    image_url: str
    freshness_note: str
