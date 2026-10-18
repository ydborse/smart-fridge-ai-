import logging
from sqlalchemy import text, inspect
from app.database import engine

logger = logging.getLogger(__name__)

def run_migrations():
    """
    Applies non-destructive schema migrations for existing SQLite databases.
    Ensures new columns exist in users, alerts, and notifications_log tables.
    """
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    with engine.connect() as conn:
        # 1. Check and add columns to 'users' table
        if "users" in existing_tables:
            user_cols = {col["name"] for col in inspector.get_columns("users")}
            new_user_cols = [
                ("sms_for_expiring", "BOOLEAN DEFAULT 0"),
                ("sms_for_expired", "BOOLEAN DEFAULT 1"),
                ("sms_for_temperature", "BOOLEAN DEFAULT 1"),
                ("sms_for_dairy", "BOOLEAN DEFAULT 1"),
                ("sms_repeat_interval_minutes", "INTEGER DEFAULT 15"),
                ("sms_max_duration_minutes", "INTEGER DEFAULT 120"),
                ("spoilage_reminder_enabled", "BOOLEAN DEFAULT 1"),
                ("spoilage_reminder_interval_minutes", "INTEGER DEFAULT 120"),
                ("push_for_spoilage", "BOOLEAN DEFAULT 1"),
                ("telegram_notifications_enabled", "BOOLEAN DEFAULT 1"),
                ("telegram_chat_id", "VARCHAR(100)"),
            ]
            for col_name, col_type in new_user_cols:
                if col_name not in user_cols:
                    logger.info(f"Adding column '{col_name}' to 'users' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Could not add {col_name} to users: {e}")

            # Clean up any stale dummy/mock chat IDs from previous test runs
            try:
                conn.execute(text("UPDATE users SET telegram_chat_id = NULL WHERE telegram_chat_id IN ('554433221', 'PASTE_YOUR_CHAT_ID_HERE', 'your_telegram_chat_id')"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Could not sanitize stale telegram_chat_id in users: {e}")

        # 2. Check and add columns to 'alerts' table
        if "alerts" in existing_tables:
            alert_cols = {col["name"] for col in inspector.get_columns("alerts")}
            new_alert_cols = [
                ("is_resolved", "BOOLEAN DEFAULT 0"),
                ("resolved_at", "DATETIME"),
                ("first_sms_sent_at", "DATETIME"),
                ("last_sms_sent_at", "DATETIME"),
                ("next_sms_scheduled_at", "DATETIME"),
                ("sms_repeat_count", "INTEGER DEFAULT 0"),
                ("status", "VARCHAR(20) DEFAULT 'ACTIVE'"),
                ("confidence_score", "FLOAT"),
                ("last_notification_at", "DATETIME"),
                ("next_reminder_at", "DATETIME"),
                ("reminder_count", "INTEGER DEFAULT 0"),
                ("action_recommended", "VARCHAR(255) DEFAULT 'Remove or inspect this food item'"),
                ("evidence_type", "VARCHAR(50) DEFAULT 'freshness_assessment'"),
                ("evidence_details", "TEXT"),
            ]
            for col_name, col_type in new_alert_cols:
                if col_name not in alert_cols:
                    logger.info(f"Adding column '{col_name}' to 'alerts' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE alerts ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Could not add {col_name} to alerts: {e}")

            # Backfill any null status/reminder values in alerts
            try:
                conn.execute(text("UPDATE alerts SET status = 'RESOLVED' WHERE is_resolved = 1 AND (status IS NULL OR status = 'ACTIVE')"))
                conn.execute(text("UPDATE alerts SET status = 'ACTIVE' WHERE (is_resolved = 0 OR is_resolved IS NULL) AND status IS NULL"))
                conn.execute(text("UPDATE alerts SET next_reminder_at = next_sms_scheduled_at WHERE next_reminder_at IS NULL AND next_sms_scheduled_at IS NOT NULL"))
                conn.execute(text("UPDATE alerts SET last_notification_at = last_sms_sent_at WHERE last_notification_at IS NULL AND last_sms_sent_at IS NOT NULL"))
                conn.execute(text("UPDATE alerts SET reminder_count = sms_repeat_count WHERE (reminder_count IS NULL OR reminder_count = 0) AND sms_repeat_count > 0"))
                conn.commit()
            except Exception as e:
                logger.warning(f"Backfill alerts data warning: {e}")

        # 3. Check and add columns to 'notifications_log' table
        if "notifications_log" in existing_tables:
            log_cols = {col["name"] for col in inspector.get_columns("notifications_log")}
            new_log_cols = [
                ("alert_id", "INTEGER REFERENCES alerts(id)"),
                ("food_name", "VARCHAR(255)"),
                ("provider_message_id", "VARCHAR(100)"),
                ("repeat_count", "INTEGER DEFAULT 1"),
                ("next_reminder_at", "DATETIME"),
            ]
            for col_name, col_type in new_log_cols:
                if col_name not in log_cols:
                    logger.info(f"Adding column '{col_name}' to 'notifications_log' table...")
                    try:
                        conn.execute(text(f"ALTER TABLE notifications_log ADD COLUMN {col_name} {col_type}"))
                        conn.commit()
                    except Exception as e:
                        logger.warning(f"Could not add {col_name} to notifications_log: {e}")

    logger.info("Database schema migration verification completed.")
