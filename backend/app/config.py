from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from typing import Optional
import os

class Settings(BaseSettings):
    PROJECT_NAME: str = "Smart Fridge"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = "smart_fridge_super_secret_jwt_key_2026_change_in_prod"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    APP_URL: str = "http://localhost:5173"

    # Database: Default to SQLite file anchored to project root
    DATABASE_URL: str = f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'smart_fridge.db')).replace(os.sep, '/')}"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_db_url(cls, v: Optional[str]) -> str:
        if v and v.startswith("sqlite:///") and not v.startswith("sqlite:////") and not (len(v) > 11 and v[10] == ":"):
            rel_path = v.replace("sqlite:///", "")
            backend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            project_root = os.path.abspath(os.path.join(backend_dir, ".."))
            cand1 = os.path.abspath(os.path.join(backend_dir, rel_path))
            cand2 = os.path.abspath(os.path.join(project_root, rel_path))
            target = cand1 if os.path.exists(cand1) else cand2
            return f"sqlite:///{target.replace(os.sep, '/')}"
        return v or f"sqlite:///{os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'smart_fridge.db')).replace(os.sep, '/')}"

    # 1. Email Provider Config (SMTP / Resend / Brevo)
    EMAIL_PROVIDER: str = "smtp"  # 'smtp', 'resend', or 'brevo'
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = "smartfridge843@gmail.com"
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_NAME: str = "Smart Fridge Assistant"
    EMAILS_FROM_EMAIL: str = "smartfridge843@gmail.com"
    EMAIL_FROM: Optional[str] = "smartfridge843@gmail.com"
    RESEND_API_KEY: Optional[str] = None
    BREVO_API_KEY: Optional[str] = None

    # 2. Web Push (VAPID) Config
    WEB_PUSH_ENABLED: bool = True
    VAPID_PUBLIC_KEY: str = "BKHP_lRxFvV3_MOAYFSLq5gpWbxxwB9NH6lZDPgHsAU6zhujqyRYy1cs6-P-E8WAhUV6GvVlVCG07TgpNz7BjIk"
    VAPID_PRIVATE_KEY: str = "1hwwXkj035YuZW4m53khj2jaK0j211AG5zPk4WXZdKU"
    VAPID_CLAIM_EMAIL: str = "admin@smartfridge.local"

    # 3. Telegram Bot API Config (Primary Provider)
    TELEGRAM_BOT_TOKEN: Optional[str] = None
    TELEGRAM_CHAT_ID: Optional[str] = None
    TELEGRAM_ENABLED: bool = True

    @field_validator("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", mode="before")
    @classmethod
    def clean_telegram_credentials(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        s = str(v).strip()
        # Strip inline comments (e.g. 123456 # chat id) if not enclosed in quotes
        if "#" in s and not ((s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'"))):
            s = s.split("#")[0].strip()
        if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
            s = s[1:-1].strip()
        return s or None

    @property
    def telegram_configured(self) -> bool:
        token = (self.TELEGRAM_BOT_TOKEN or "").strip()
        chat_id = str(self.TELEGRAM_CHAT_ID or "").strip()
        return bool(
            token
            and chat_id
            and "PASTE_YOUR" not in token
            and "PASTE_YOUR" not in chat_id
            and token != "your_telegram_bot_token"
            and chat_id != "your_telegram_chat_id"
        )

    # 4. Legacy SMS Provider Config (Twilio / Fast2SMS)
    TWILIO_ACCOUNT_SID: Optional[str] = None
    TWILIO_AUTH_TOKEN: Optional[str] = None
    TWILIO_FROM_NUMBER: Optional[str] = None
    TWILIO_TO_NUMBER: Optional[str] = None
    TWILIO_ENABLED: Optional[bool] = None

    SMS_ENABLED: bool = False
    SMS_PROVIDER: str = "twilio"  # 'twilio' or 'fast2sms'
    SMS_TO_NUMBER: Optional[str] = None
    TWILIO_MESSAGING_SERVICE_SID: Optional[str] = None
    FAST2SMS_API_KEY: Optional[str] = None
    FAST2SMS_DLT_TE_ID: Optional[str] = None

    @model_validator(mode="after")
    def sync_twilio_settings(self):
        # Synchronize TWILIO_ENABLED and legacy SMS_ENABLED
        if self.TWILIO_ENABLED is not None:
            self.SMS_ENABLED = bool(self.TWILIO_ENABLED)
        else:
            self.TWILIO_ENABLED = bool(self.SMS_ENABLED)

        # Synchronize TWILIO_TO_NUMBER and legacy SMS_TO_NUMBER
        if self.TWILIO_TO_NUMBER and not self.SMS_TO_NUMBER:
            self.SMS_TO_NUMBER = self.TWILIO_TO_NUMBER
        elif self.SMS_TO_NUMBER and not self.TWILIO_TO_NUMBER:
            self.TWILIO_TO_NUMBER = self.SMS_TO_NUMBER
        return self

    # SMS Repeat & Rate Limiting
    SMS_REMINDER_INTERVAL_MINUTES: int = 120  # Default 2-hour interval between repeat SMS alerts
    SMS_DEFAULT_REPEAT_INTERVAL_MINUTES: int = 120
    SMS_DEFAULT_MAX_DURATION_MINUTES: int = 120  # 2 hours max repeat limit
    SMS_COOLDOWN_SECONDS: int = 60  # Minimum gap between sends to avoid spam

    # Kaggle Credentials for Dataset Downloads
    KAGGLE_USERNAME: Optional[str] = None
    KAGGLE_KEY: Optional[str] = None

    # Storage Paths
    STORAGE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage"))
    UPLOAD_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "uploads"))
    FOOD_IMG_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "foods"))
    AUDIT_IMG_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "storage", "audit"))

    # ML Model Paths
    MODEL_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "best_model.pth"))
    FOOD_MODEL_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "food_classifier.pth"))
    FRESHNESS_MODEL_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "ml", "models", "freshness_classifier.pth"))

    model_config = {
        "env_file": [
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env")),
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".env")),
            ".env"
        ],
        "extra": "allow"
    }

settings = Settings()

# Ensure directories exist
os.makedirs(settings.STORAGE_DIR, exist_ok=True)
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.FOOD_IMG_DIR, exist_ok=True)
os.makedirs(settings.AUDIT_IMG_DIR, exist_ok=True)
