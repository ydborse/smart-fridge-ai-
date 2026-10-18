export interface User {
  id: number;
  email: string;
  full_name: string;
  phone_number?: string;
  email_notifications_enabled?: boolean;
  push_notifications_enabled?: boolean;
  sms_notifications_enabled?: boolean;
  push_subscription?: string;
  has_push_subscription?: boolean;
  email_for_expiring?: boolean;
  email_for_expired?: boolean;
  email_daily_digest?: boolean;
  push_for_expiring?: boolean;
  push_for_expired?: boolean;
  push_for_temperature?: boolean;
  sms_for_critical?: boolean;
  sms_for_expiring?: boolean;
  sms_for_expired?: boolean;
  sms_for_temperature?: boolean;
  sms_for_dairy?: boolean;
  sms_repeat_interval_minutes?: number;
  sms_max_duration_minutes?: number;
  spoilage_reminder_enabled?: boolean;
  spoilage_reminder_interval_minutes?: number;
  push_for_spoilage?: boolean;
  alert_lead_days: number;
  quiet_hours_start: string;
  quiet_hours_end: string;
  audit_day: string;
  audit_time: string;
}

export interface NotificationLog {
  id: number;
  user_id: number;
  alert_id?: number;
  food_name?: string;
  provider_message_id?: string;
  repeat_count?: number;
  channel: string;
  provider?: string;
  recipient?: string;
  title: string;
  message: string;
  status: 'pending' | 'accepted' | 'delivered' | 'simulated' | 'failed' | string;
  error_message?: string;
  attempts: number;
  created_at: string;
  sent_at?: string;
  next_reminder_at?: string;
}

export interface SchedulerStatus {
  status: string;
  scheduler_running: boolean;
  active_spoilage_incidents: number;
  recurring_interval_minutes: number;
  reminders_enabled: boolean;
  jobs: Array<{
    id: string;
    name: string;
    next_run_time?: string;
  }>;
}

export interface Zone {
  id: number;
  name: string;
  code: string;
  target_temp_min: number;
  target_temp_max: number;
  target_humidity_min: number;
  target_humidity_max: number;
  current_temp: number;
  current_humidity: number;
  health_score: number;
  status: 'normal' | 'warning' | 'critical';
  description?: string;
  item_count?: number;
  items?: Array<{
    id: number;
    name: string;
    category: string;
    freshness_status: string;
  }>;
  compatibility_conflict?: boolean;
  producers?: string[];
  sensitive?: string[];
}

export interface FoodItem {
  id: number;
  user_id: number;
  name: string;
  category: string;
  item_type: 'fruit' | 'vegetable' | 'packaged';
  zone_id: number;
  zone_name?: string;
  zone_code?: string;
  quantity: number;
  unit: string;
  added_at: string;
  expiry_date: string;
  freshness_status: 'Fresh' | 'Ripe' | 'Overripe' | 'Rotten' | 'Expiring Soon' | 'Expired';
  barcode?: string;
  brand?: string;
  image_path?: string;
  source: 'fruit_scan' | 'barcode_scan' | 'manual';
  is_used: boolean;
  is_discarded: boolean;
  estimated_cost: number;
  notes?: string;
  days_until_expiry?: number;
}

export interface AlertItem {
  id: number;
  food_item_id?: number;
  food_item_name?: string;
  zone_id?: number;
  zone_name?: string;
  alert_type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  is_read: boolean;
  is_resolved?: boolean;
  status?: 'ACTIVE' | 'REMOVED' | 'RESOLVED' | string;
  confidence_score?: number;
  last_notification_at?: string;
  next_reminder_at?: string;
  reminder_count?: number;
  action_recommended?: string;
  food_item_category?: string;
  resolved_at?: string;
  first_sms_sent_at?: string;
  last_sms_sent_at?: string;
  next_sms_scheduled_at?: string;
  sms_repeat_count?: number;
  evidence_type?: string;
  evidence_details?: string;
  channel_sent?: string;
  created_at: string;
}

export interface DashboardSummary {
  stats: {
    total_items: number;
    fresh_items: number;
    expiring_soon_items: number;
    expired_items: number;
  };
  insights: string[];
  expiring_soon: FoodItem[];
  recently_added: FoodItem[];
  zone_stats: Array<{
    id: number;
    name: string;
    code: string;
    temperature: number;
    humidity: number;
    health_score: number;
    status: string;
    item_count: number;
  }>;
  temperature_history_24h: Array<{
    time: string;
    top_shelf?: number;
    middle_shelf?: number;
    bottom_shelf?: number;
    veg_drawer?: number;
    freezer?: number;
    top_hum?: number;
    middle_hum?: number;
    bottom_hum?: number;
    veg_hum?: number;
  }>;
  unread_alerts_count: number;
}

export interface PredictionItem {
  item_name: string;
  freshness_class: string;
  confidence: number;
  typical_shelf_life_days: number;
  suggested_expiry_date: string;
  suggested_zone_id: number;
  suggested_zone_name: string;
  category: string;
  item_type: 'fruit' | 'vegetable' | 'packaged' | 'other';
  needs_manual_check: boolean;
  freshness_confidence?: number;
  condition_notes?: string;
  is_dairy?: boolean;
  is_unknown?: boolean;
  brand?: string;
  extracted_date?: string;
  date_type?: string;
  date_status?: string;
  ocr_confidence?: number;
  is_estimated?: boolean;
  detected_text?: string;
}

export interface PredictionResponse {
  top_prediction: PredictionItem;
  all_predictions: PredictionItem[];
  image_url: string;
  is_demo_mode?: boolean;
  disclaimer: string;
}

export interface DairyPredictionResponse {
  category: 'milk' | 'yogurt' | 'paneer' | 'cheese' | string;
  display_name: string;
  confidence: number;
  all_scores: Record<string, number>;
  suggested_shelf: string;
  suggested_zone_id: number;
  suggested_zone_code: string;
  typical_shelf_life_days: number;
  suggested_expiry_date: string;
  storage_tips: string;
  needs_manual_check: boolean;
  user_guidance?: string;
  is_dairy: boolean;
  image_url: string;
  freshness_note: string;
}

export interface BarcodeProduct {
  barcode: string;
  name: string;
  brand?: string;
  category: string;
  image_url?: string;
  quantity_str?: string;
  nutri_score?: string;
  default_shelf_life_days: number;
  suggested_expiry_date: string;
  suggested_zone_id: number;
  suggested_zone_name: string;
}

export interface AuditSession {
  id: number;
  status: string;
  total_detected: number;
  matched_count: number;
  missing_count: number;
  unknown_count: number;
  notes?: string;
  created_at: string;
  results: Array<{
    id: number;
    food_item_id?: number;
    detected_name?: string;
    detected_freshness?: string;
    image_path?: string;
    status: 'matched' | 'missing' | 'unknown';
    resolution?: string;
  }>;
}

export interface ActivityHistoryItem {
  id: number;
  action: 'added' | 'used' | 'discarded' | 'expired' | 'updated';
  food_item_name: string;
  quantity: number;
  unit: string;
  estimated_cost: number;
  timestamp: string;
}
