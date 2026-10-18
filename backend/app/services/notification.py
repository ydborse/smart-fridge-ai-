import re
import uuid
import json
import html
import logging
import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

import httpx
from sqlalchemy.orm import Session
from app.config import settings
from app.models import User, NotificationLog

try:
    from twilio.rest import Client
    from twilio.base.exceptions import TwilioRestException
except ImportError:
    Client = None
    TwilioRestException = Exception

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. HTML Email Templates & Rendering
# ==============================================================================

def render_alert_email_html(title: str, message: str, metadata: Optional[Dict[str, Any]] = None) -> str:
    metadata = metadata or {}
    food_name = metadata.get("food_name", "Pantry Item")
    expiry_date = metadata.get("expiry_date", "Soon")
    status = metadata.get("status", "Attention")
    image_url = metadata.get("image_url")
    food_id = metadata.get("food_item_id")
    action_url = metadata.get("action_url") or f"{settings.APP_URL}/foods"
    if food_id:
        action_url = f"{settings.APP_URL}/foods?action=mark_used&id={food_id}"

    status_color = "#f43f5e" if status in ["Expired", "Rotten"] else "#f59e0b" if status in ["Expiring Soon", "Ripe", "Overripe"] else "#22c55e"
    status_bg = "#fff1f2" if status in ["Expired", "Rotten"] else "#fef3c7" if status in ["Expiring Soon", "Ripe", "Overripe"] else "#f0fdf4"

    img_html = ""
    if image_url:
        full_img_url = image_url if image_url.startswith("http") else f"{settings.APP_URL}{image_url}"
        img_html = f'''
        <div style="text-align: center; margin: 16px 0;">
            <img src="{full_img_url}" alt="{food_name}" style="max-width: 220px; max-height: 180px; border-radius: 12px; object-fit: cover; border: 1px solid #e2e8f0; box-shadow: 0 2px 8px rgba(0,0,0,0.06);" />
        </div>
        '''

    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 24px; color: #1e293b; }}
            .container {{ max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; border: 1px solid #e2e8f0; box-shadow: 0 4px 20px rgba(0,0,0,0.05); }}
            .header {{ background: linear-gradient(135deg, #16a34a, #22c55e); padding: 28px 24px; text-align: center; color: white; }}
            .header h1 {{ margin: 0; font-size: 22px; font-weight: 800; letter-spacing: -0.5px; }}
            .header p {{ margin: 4px 0 0 0; font-size: 13px; opacity: 0.9; }}
            .content {{ padding: 24px; }}
            .alert-card {{ background: #f8fafc; border-radius: 14px; padding: 18px; border: 1px solid #e2e8f0; margin-bottom: 20px; }}
            .status-badge {{ display: inline-block; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: 700; color: {status_color}; background-color: {status_bg}; }}
            .btn {{ display: block; text-align: center; background: #22c55e; color: #ffffff !important; padding: 12px 24px; border-radius: 12px; font-size: 14px; font-weight: 700; text-decoration: none; box-shadow: 0 2px 10px rgba(34, 197, 94, 0.3); }}
            .footer {{ padding: 16px 24px; background: #f8fafc; border-top: 1px solid #e2e8f0; text-align: center; font-size: 11px; color: #94a3b8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Smart Fridge Assistant</h1>
                <p>Smart Food. Healthy You.</p>
            </div>
            <div class="content">
                <div class="alert-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span class="status-badge">{status}</span>
                        <span style="font-size: 12px; color: #64748b;">Expires: <strong>{expiry_date}</strong></span>
                    </div>
                    <div style="font-size: 16px; font-weight: 700; color: #0f172a; margin: 4px 0;">{food_name}</div>
                    <h2 style="margin: 6px 0; font-size: 15px; color: #334155; font-weight: 600;">{title}</h2>
                    <p style="margin: 4px 0 0 0; font-size: 13px; color: #475569; line-height: 1.5;">{message}</p>
                    {img_html}
                </div>
                <a href="{action_url}" class="btn">Mark as Used / Consumed</a>
            </div>
            <div class="footer">
                Freshness predictions are assistive and not a food safety guarantee.<br>
                Configure email lead times and quiet hours in your Smart Fridge Settings.
            </div>
        </div>
    </body>
    </html>
    """

def render_daily_digest_html(items: List[Dict[str, Any]]) -> str:
    rows = ""
    for item in items:
        rows += f"""
        <tr style="border-bottom: 1px solid #f1f5f9;">
            <td style="padding: 10px 8px; font-weight: 600; font-size: 13px; color: #1e293b;">{item.get('name')}</td>
            <td style="padding: 10px 8px; font-size: 12px; color: #64748b;">{item.get('zone')}</td>
            <td style="padding: 10px 8px; font-size: 12px; font-weight: 700; color: #f59e0b;">{item.get('days_left')} day(s) left</td>
            <td style="padding: 10px 8px; text-align: right;">
                <a href="{settings.APP_URL}/foods?action=mark_used&id={item.get('id')}" style="font-size: 11px; font-weight: 700; color: #16a34a; text-decoration: none;">Mark Used</a>
            </td>
        </tr>
        """

    return f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; background: #f8fafc; padding: 24px;">
        <div style="max-width: 540px; margin: 0 auto; background: #ffffff; border-radius: 20px; overflow: hidden; border: 1px solid #e2e8f0;">
            <div style="background: linear-gradient(135deg, #16a34a, #22c55e); padding: 24px; text-align: center; color: white;">
                <h1 style="margin: 0; font-size: 20px;">Daily Pantry Digest 🍳</h1>
                <p style="margin: 4px 0 0 0; font-size: 12px; opacity: 0.9;">Items expiring soon in your Smart Fridge</p>
            </div>
            <div style="padding: 20px;">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr style="border-bottom: 2px solid #e2e8f0; font-size: 11px; color: #94a3b8; text-transform: uppercase;">
                            <th style="padding: 8px; text-align: left;">Item</th>
                            <th style="padding: 8px; text-align: left;">Shelf</th>
                            <th style="padding: 8px; text-align: left;">Remaining</th>
                            <th style="padding: 8px; text-align: right;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows}
                    </tbody>
                </table>
                <div style="margin-top: 24px; text-align: center;">
                    <a href="{settings.APP_URL}/foods" style="display: inline-block; background: #22c55e; color: white; padding: 10px 20px; border-radius: 10px; font-size: 13px; font-weight: 700; text-decoration: none;">Open Pantry Inventory</a>
                </div>
            </div>
        </div>
    </body>
    </html>
    """

# ==============================================================================
# 2. Email Provider Implementations (SMTP / Resend / Brevo)
# ==============================================================================

async def send_via_smtp(to_email: str, subject: str, html_body: str) -> None:
    if not (settings.SMTP_USER and settings.SMTP_PASSWORD):
        logger.info(f"[EMAIL SIMULATED - SMTP] To: {to_email} | Subject: {subject}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{settings.EMAILS_FROM_NAME} <{settings.SMTP_USER}>"
    msg["To"] = to_email
    msg.attach(MIMEText(html_body, "html"))

    def _sync_smtp_send():
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_smtp_send)
    logger.info(f"Email sent successfully via SMTP to {to_email}")


async def send_via_resend(to_email: str, subject: str, html_body: str) -> None:
    if not settings.RESEND_API_KEY:
        logger.info(f"[EMAIL SIMULATED - Resend] To: {to_email} | Subject: {subject}")
        return

    url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {settings.RESEND_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": f"{settings.EMAILS_FROM_NAME} <{settings.EMAILS_FROM_EMAIL}>",
        "to": [to_email],
        "subject": subject,
        "html": html_body
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code not in [200, 201]:
            raise Exception(f"Resend API error {resp.status_code}: {resp.text}")
    logger.info(f"Email sent successfully via Resend to {to_email}")


async def send_via_brevo(to_email: str, subject: str, html_body: str) -> None:
    if not settings.BREVO_API_KEY:
        logger.info(f"[EMAIL SIMULATED - Brevo] To: {to_email} | Subject: {subject}")
        return

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "api-key": settings.BREVO_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "sender": {"name": settings.EMAILS_FROM_NAME, "email": settings.EMAILS_FROM_EMAIL},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(url, json=payload, headers=headers)
        if resp.status_code not in [200, 201]:
            raise Exception(f"Brevo API error {resp.status_code}: {resp.text}")
    logger.info(f"Email sent successfully via Brevo to {to_email}")


async def dispatch_email(to_email: str, subject: str, html_body: str) -> str:
    provider = settings.EMAIL_PROVIDER.lower()
    if provider == "resend":
        await send_via_resend(to_email, subject, html_body)
        return "resend"
    elif provider == "brevo":
        await send_via_brevo(to_email, subject, html_body)
        return "brevo"
    else:
        await send_via_smtp(to_email, subject, html_body)
        return "smtp"

# ==============================================================================
# 3. Web Push Provider (VAPID / pywebpush)
# ==============================================================================

async def dispatch_web_push(
    subscription_json: str,
    title: str,
    message: str,
    metadata: Optional[Dict[str, Any]] = None,
    user: Optional[User] = None,
    db: Optional[Session] = None
) -> str:
    if not subscription_json:
        logger.info(f"[WEB PUSH SIMULATED] No subscription registered. Title: {title}")
        return "vapid_simulated"

    is_placeholder_vapid = (
        not settings.VAPID_PRIVATE_KEY
        or "YOUR_" in str(settings.VAPID_PRIVATE_KEY)
        or settings.VAPID_PRIVATE_KEY == "your_vapid_private_key"
    )
    if is_placeholder_vapid:
        logger.info(f"[WEB PUSH SIMULATED] VAPID keys not configured in backend/.env. Title: {title}")
        return "vapid_simulated"

    try:
        sub_info = json.loads(subscription_json)
    except Exception as e:
        raise ValueError(f"Invalid subscription JSON: {e}")

    alert_id = metadata.get("alert_id") if metadata else None
    action_url = metadata.get("action_url", "/alerts") if metadata else "/alerts"
    tag = f"spoilage-alert-{alert_id}" if alert_id else "smart-fridge-alert"

    payload = json.dumps({
        "title": title,
        "body": message,
        "icon": "/favicon.svg",
        "badge": "/favicon.svg",
        "tag": tag,
        "data": {
            "url": action_url,
            "alert_id": alert_id,
            "food_item_id": metadata.get("food_item_id") if metadata else None,
            "action_recommended": metadata.get("action_recommended", "Remove or inspect this food item") if metadata else None
        }
    })

    def _sync_webpush():
        from pywebpush import webpush, WebPushException
        try:
            webpush(
                subscription_info=sub_info,
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"},
                ttl=3600
            )
        except WebPushException as ex:
            # Check for HTTP 404 / 410 Gone (expired or invalid subscription)
            status_code = getattr(getattr(ex, "response", None), "status_code", None)
            if status_code in (404, 410) or "410" in str(ex) or "404" in str(ex):
                logger.warning(f"Web Push subscription expired (HTTP {status_code}). Removing subscription for user.")
                if db and user:
                    user.push_subscription = None
                    user.push_notifications_enabled = False
                    db.commit()
            raise ex

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_webpush)
    logger.info("Web push dispatched successfully via VAPID")
    return "vapid"

# ==============================================================================
# 4. SMS Provider Implementations (Twilio / Fast2SMS) & Formatting
# ==============================================================================

def normalize_phone_number(phone: str) -> str:
    """
    Normalizes phone numbers to standard E.164 format.
    Handles Indian mobile numbers (+91), US numbers (+1), and formats properly.
    """
    if not phone:
        return ""
    cleaned = re.sub(r'[\s\-\(\)\.]', '', str(phone).strip())
    # 10 digits starting with 6, 7, 8, or 9 -> Indian mobile (+91)
    if re.match(r'^[6-9]\d{9}$', cleaned):
        return f"+91{cleaned}"
    # 11 digits starting with 0 followed by 10 Indian digits
    if re.match(r'^0[6-9]\d{9}$', cleaned):
        return f"+91{cleaned[1:]}"
    # 12 digits starting with 91
    if re.match(r'^91[6-9]\d{9}$', cleaned):
        return f"+{cleaned}"
    # Already starting with +
    if cleaned.startswith("+"):
        return cleaned
    # 10 digits starting with 2-9 (US/Canada format)
    if re.match(r'^[2-9]\d{9}$', cleaned):
        return f"+1{cleaned}"
    return f"+{cleaned}" if not cleaned.startswith("+") else cleaned


DAIRY_KEYWORDS = {"milk", "yogurt", "curd", "dahi", "cheese", "paneer", "butter", "cream", "lassi", "buttermilk"}

def is_dairy_item(name: Optional[str] = None, category: Optional[str] = None) -> bool:
    """
    Checks if a product is a dairy product (milk, yogurt/curd, cheese, paneer, etc.).
    """
    if category and any(k in category.lower() for k in ["dairy", "packaged_milk", "packaged_yogurt", "packaged_paneer", "cheese"]):
        return True
    if name:
        n = name.lower()
        return any(k in n for k in DAIRY_KEYWORDS)
    return False


def format_detection_time(dt: Optional[Any]) -> str:
    """
    Formats detection time to standard 12-hour clock (e.g. '10:00 AM' or '12:15 PM').
    """
    if not dt:
        return datetime.now().strftime("%I:%M %p").lstrip("0")
    if isinstance(dt, datetime):
        return dt.strftime("%I:%M %p").lstrip("0")
    if isinstance(dt, str):
        if "AM" in dt or "PM" in dt:
            return dt
        try:
            parsed = datetime.fromisoformat(dt.replace("Z", "+00:00"))
            return parsed.strftime("%I:%M %p").lstrip("0")
        except Exception:
            return dt
    return str(dt)


def format_sms_alert(
    title: str,
    message: str,
    food_name: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    days_until_expiry: Optional[int] = None,
    temp_c: Optional[float] = None,
    zone_name: Optional[str] = None,
    repeat_count: int = 1,
    status: Optional[str] = None,
    detection_time: Optional[Any] = None
) -> str:
    """
    Constructs a concise (<160 characters) SMS alert message.
    Adheres strictly to project requirements:
    1. Spoilage Detection Alert:
       "SMART FRIDGE ALERT: Your Apple in Zone A is detected as spoiled. Please inspect and remove it from your fridge. Detection time: 10:00 AM."
    2. Spoilage Recurring Reminder (every 2 hours):
       "SMART FRIDGE REMINDER: Your Apple in Zone A is still marked as spoiled. Please remove it from the fridge. This is reminder 2."
    3. Temperature Alert:
       "SMART FRIDGE ALERT: Refrigerator temperature is above the safe configured limit. Please check the fridge."
    4. Dairy Expired:
       "SMART FRIDGE ALERT: Your yogurt has expired. Please inspect it before consumption."
    5. Dairy Expiring Soon:
       "SMART FRIDGE ALERT: Your milk is nearing its expiry date. Please check the expiry information."
    """
    is_dairy = is_dairy_item(food_name, category)
    item_display = food_name.capitalize() if food_name else "Item"
    loc = f" in {zone_name}" if zone_name else ""

    # Check if this alert is a spoilage alert (food spoiled/rotten/expired)
    is_spoilage_alert = (
        alert_type in ["Food Spoilage Alert", "Expired / Remove Now"] or
        (status and status.lower() in ["rotten", "spoiled", "expired"]) or
        ("spoiled" in title.lower()) or
        ("rotten" in title.lower())
    )

    # 1. 2-Hour Spoilage Recurring Reminder (repeat_count > 1)
    if repeat_count > 1 and is_spoilage_alert:
        status_word = status.lower() if status else ("expired" if is_dairy else "spoiled")
        if status_word == "rotten":
            status_word = "spoiled"
        full_msg = f"SMART FRIDGE REMINDER: Your {item_display}{loc} is still marked as {status_word}. Please remove it from the fridge. This is reminder {repeat_count}."
        if len(full_msg) > 160:
            return full_msg[:157] + "..."
        return full_msg

    # 2. First Spoilage Alert (repeat_count == 1) when detection_time or zone_name or alert_type == "Food Spoilage Alert"
    if is_spoilage_alert and (detection_time or zone_name or alert_type == "Food Spoilage Alert"):
        status_word = status.lower() if status else ("expired" if is_dairy else "spoiled")
        if status_word == "rotten":
            status_word = "spoiled"
        time_str = format_detection_time(detection_time)
        full_msg = f"SMART FRIDGE ALERT: Your {item_display}{loc} is detected as {status_word}. Please inspect and remove it from your fridge. Detection time: {time_str}."
        if len(full_msg) > 160:
            return full_msg[:157] + "..."
        return full_msg

    prefix = "SMART FRIDGE ALERT:"
    if repeat_count > 1:
        prefix = f"SMART FRIDGE ALERT (Reminder #{repeat_count}):"

    # 3. Temperature Warning
    if alert_type == "Temperature Warning" or (temp_c is not None) or ("temperature" in title.lower()):
        if temp_c is not None and zone_name:
            body = f"Refrigerator temperature is above the safe configured limit ({temp_c}°C in {zone_name}). Please check the fridge."
        else:
            body = "Refrigerator temperature is above the safe configured limit. Please check the fridge."

    # 4. Dairy Expired (standalone format)
    elif is_dairy and (alert_type == "Expired / Remove Now" or severity == "critical" or "expired" in title.lower() or "spoiled" in title.lower()):
        body = f"Your {item_display.lower()} has expired. Please inspect it before consumption."

    # 5. Dairy Expiring Soon
    elif is_dairy and (alert_type == "Expiring Soon" or "expiring" in title.lower()):
        body = f"Your {item_display.lower()} is nearing its expiry date. Please check the expiry information."

    # 6. General Food Expired
    elif alert_type == "Expired / Remove Now" or severity == "critical" or "spoiled" in title.lower() or "expired" in title.lower():
        body = f"Your {item_display.lower()} has expired. Please remove it from the fridge."

    # 7. General Food Expiring Soon
    elif alert_type == "Expiring Soon" or "expiring" in title.lower():
        days_str = f"in {days_until_expiry} day(s)" if days_until_expiry is not None else "soon"
        body = f"Your {item_display.lower()} is nearing its expiry date ({days_str}). Please use it soon."

    # 8. Fallback
    else:
        clean_msg = message.replace("\n", " ").strip()
        body = clean_msg if clean_msg else title

    full_msg = f"{prefix} {body}".strip()
    if len(full_msg) > 160:
        return full_msg[:157] + "..."
    return full_msg


# ==============================================================================
# 5. Telegram Bot API Implementation (Primary Notification Provider)
# ==============================================================================

def sanitize_telegram_token(text: Optional[str], token: Optional[str] = None) -> str:
    """
    Scrubs Telegram bot tokens and authentication credentials from error strings, URLs, and logs.
    Guarantees that bot tokens are never logged, printed, or returned to clients.
    """
    if not text:
        return ""
    cleaned = str(text)
    active_token = token or getattr(settings, "TELEGRAM_BOT_TOKEN", None)
    if active_token and active_token in cleaned:
        cleaned = cleaned.replace(active_token, "[REDACTED_BOT_TOKEN]")
    # Redact Telegram bot token format: 123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
    cleaned = re.sub(r'bot\d{6,12}:[A-Za-z0-9_-]+', 'bot[REDACTED_BOT_TOKEN]', cleaned)
    cleaned = re.sub(r'\b\d{6,12}:[A-Za-z0-9_-]{30,50}\b', '[REDACTED_BOT_TOKEN]', cleaned)
    # Redact general credentials
    cleaned = re.sub(r'(token|key|secret|password|auth)=([^\s&]+)', r'\1=***', cleaned, flags=re.IGNORECASE)
    return cleaned


def format_telegram_alert(
    title: str,
    message: str,
    food_name: Optional[str] = None,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    days_until_expiry: Optional[int] = None,
    temp_c: Optional[float] = None,
    zone_name: Optional[str] = None,
    repeat_count: int = 1,
    status: Optional[str] = None,
    detection_time: Optional[Any] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> str:
    """
    Constructs a rich, visually styled HTML message for Telegram Bot delivery.
    Escapes dynamic content using html.escape to avoid Telegram parse errors.
    """
    metadata = metadata or {}
    esc = lambda s: html.escape(str(s)) if s is not None else ""

    item_name = esc(food_name or metadata.get("food_name") or "Food Item")
    loc = esc(zone_name or metadata.get("zone_name") or "Refrigerator")
    status_str = esc(status or metadata.get("status") or ("Spoiled" if severity == "critical" else "Attention"))
    time_str = esc(format_detection_time(detection_time or metadata.get("detection_time")))
    action = esc(metadata.get("action_recommended") or "Inspect and remove this item from your fridge.")
    reason = esc(metadata.get("reason") or metadata.get("evidence_details") or "Freshness assessment indicated spoilage.")

    is_test = "test" in title.lower() or "test" in (alert_type or "").lower()
    if is_test:
        return (
            "✅ <b>SMART FRIDGE AI — TEST ALERT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "📡 <b>Status:</b> Telegram Bot Connected\n"
            f"💬 <b>Message:</b> {esc(message)}\n"
            f"🕒 <b>Timestamp:</b> {time_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Your Smart Fridge notification service is active and verified!</i>"
        )

       # Format grouped food alerts for Telegram
    grouped_items = metadata.get("food_items")

    if isinstance(grouped_items, list) and grouped_items:
        lines = [
            f"🚨 <b>SMART FRIDGE FOOD ALERTS ({len(grouped_items)})</b>",
            "━━━━━━━━━━━━━━━━━━━━━",
        ]

        for item in grouped_items:
            if not isinstance(item, dict):
                continue

            name = esc(item.get("name") or item.get("food_name") or "Food item")
            status_text = esc(item.get("status") or "Needs attention")
            zone = esc(item.get("zone_name") or item.get("zone") or "Fridge")
            reason = esc(item.get("reason") or "")
            expiry = esc(item.get("expiry_date") or "")

            lines.append(
                f"🍎 <b>{name}</b>\n"
                f"⚠️ Status: {status_text}\n"
                f"📍 Location: {zone}"
            )

            if expiry:
                lines.append(f"📅 Expiry: {expiry}")

            if reason:
                lines.append(f"ℹ️ Reason: {reason}")

            lines.append("")

        lines.append(
            "<i>Please inspect the affected items. "
            "An expiry warning uses the recorded date; it does not "
            "by itself prove physical spoilage.</i>"
        )

        return "\n".join(lines)
    
    category_line = f"🏷️ <b>Category:</b> {esc(category)}\n" if category else ""

    # 1. 2-Hour Spoilage Recurring Reminder (repeat_count > 1)
    if repeat_count > 1:
        return (
            f"🚨 <b>SMART FRIDGE REMINDER (#{repeat_count})</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🍎 <b>Item:</b> <b>{item_name}</b>\n"
            f"{category_line}"
            f"📍 <b>Location:</b> {loc}\n"
            f"⚠️ <b>Status:</b> Still marked as {status_str}\n"
            f"ℹ️ <b>Details:</b> {reason}\n"
            f"💡 <b>Action Required:</b> {action}\n"
            f"🕒 <b>Reminder Time:</b> {time_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"<i>This reminder repeats until marked resolved in the Smart Fridge dashboard.</i>"
        )

    # 2. Temperature Warning
    is_temp = alert_type == "Temperature Warning" or temp_c is not None or "temperature" in title.lower()
    if is_temp:
        temp_val = f"{temp_c}°C" if temp_c is not None else "Above threshold"
        return (
            "🌡️ <b>SMART FRIDGE TEMPERATURE WARNING</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 <b>Zone:</b> {loc}\n"
            f"⚠️ <b>Sensor Reading:</b> {temp_val}\n"
            f"💬 <b>Alert:</b> {esc(message)}\n"
            "💡 <b>Action Required:</b> Check fridge door seal or thermostat settings.\n"
            f"🕒 <b>Detection Time:</b> {time_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Immediate attention recommended to prevent food spoilage.</i>"
        )

    # 3. Spoilage & Critical Expiry Alert
    is_spoilage = (
        alert_type in ["Food Spoilage Alert", "Expired / Remove Now"] or
        (status and status.lower() in ["rotten", "spoiled", "expired"]) or
        ("spoiled" in title.lower()) or ("rotten" in title.lower()) or
        severity == "critical"
    )
    if is_spoilage:
        return (
            "🚨 <b>SMART FRIDGE SPOILAGE ALERT</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🍎 <b>Item:</b> <b>{item_name}</b>\n"
            f"{category_line}"
            f"📍 <b>Location:</b> {loc}\n"
            f"⚠️ <b>Status:</b> {status_str}\n"
            f"ℹ️ <b>Reason:</b> {reason}\n"
            f"💡 <b>Action Required:</b> {action}\n"
            f"🕒 <b>Detection Time:</b> {time_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Please inspect and remove spoiled food to keep your fridge safe.</i>"
        )

    # 4. Expiring Soon Alert
    is_expiring = alert_type == "Expiring Soon" or "expiring" in title.lower()
    if is_expiring:
        days_str = f"in {days_until_expiry} day(s)" if days_until_expiry is not None else "soon"
        return (
            "⏳ <b>SMART FRIDGE EXPIRY WARNING</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            f"🍎 <b>Item:</b> <b>{item_name}</b>\n"
            f"{category_line}"
            f"📍 <b>Location:</b> {loc}\n"
            f"📅 <b>Expiry:</b> Expiring {days_str}\n"
            f"💡 <b>Suggestion:</b> Plan to use this item before it spoils.\n"
            f"🕒 <b>Time:</b> {time_str}\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "<i>Smart Fridge Assistant — Reduce Food Waste</i>"
        )

    # 5. General / Compatibility / Audit Alert
    return (
        f"🔔 <b>SMART FRIDGE NOTIFICATION</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Title:</b> {esc(title)}\n"
        f"💬 <b>Message:</b> {esc(message)}\n"
        f"🕒 <b>Time:</b> {time_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━\n"
        "<i>Smart Food. Healthy You.</i>"
    )


def is_valid_telegram_chat_id(val: Any) -> bool:
    """
    Validates that a Telegram chat ID is non-empty, numeric (with optional leading minus),
    and not a placeholder or stale test value.
    """
    if val is None:
        return False
    s = str(val).strip()
    if not s:
        return False
    if s in ["PASTE_YOUR_CHAT_ID_HERE", "your_telegram_chat_id", "None", "null", "undefined"]:
        return False
    clean_num = s[1:] if s.startswith("-") else s
    return clean_num.isdigit()


def resolve_telegram_chat_id(
    user: Optional[User] = None,
    metadata: Optional[Dict[str, Any]] = None,
    override_chat_id: Optional[str] = None
) -> Optional[str]:
    """
    Safely resolves the active Telegram chat ID with strict precedence and stale mock filtering.
    Priority:
    1. override_chat_id (from endpoint query parameter or manual caller)
    2. metadata.get("chat_id") / metadata.get("telegram_chat_id")
    3. settings.TELEGRAM_CHAT_ID (from backend/.env)
    4. user.telegram_chat_id (from database user record, if valid and not a placeholder/mock)
    5. Fallback phone number for SMS compatibility
    """
    metadata = metadata or {}
    if is_valid_telegram_chat_id(override_chat_id):
        return str(override_chat_id).strip()

    meta_chat = metadata.get("chat_id") or metadata.get("telegram_chat_id")
    if is_valid_telegram_chat_id(meta_chat):
        return str(meta_chat).strip()

    if is_valid_telegram_chat_id(getattr(settings, "TELEGRAM_CHAT_ID", None)):
        return str(settings.TELEGRAM_CHAT_ID).strip()

    if user and is_valid_telegram_chat_id(getattr(user, "telegram_chat_id", None)):
        return str(user.telegram_chat_id).strip()

    if user and getattr(user, "phone_number", None):
        return str(user.phone_number).strip()
    if getattr(settings, "TWILIO_TO_NUMBER", None):
        return str(settings.TWILIO_TO_NUMBER).strip()
    if getattr(settings, "SMS_TO_NUMBER", None):
        return str(settings.SMS_TO_NUMBER).strip()

    return None


async def get_telegram_diagnostic() -> Dict[str, Any]:
    """
    Safe diagnostic inspection of Telegram Bot API configuration and connectivity.
    Confirms presence and validity of bot token and chat ID WITHOUT exposing secrets.
    """
    token = (settings.TELEGRAM_BOT_TOKEN or "").strip()
    configured_chat = (settings.TELEGRAM_CHAT_ID or "").strip()

    token_present = bool(token and "PASTE_YOUR" not in token and token != "your_telegram_bot_token")
    chat_present = bool(
        configured_chat
        and "PASTE_YOUR" not in configured_chat
        and configured_chat != "your_telegram_chat_id"
        and configured_chat != "554433221"
    )

    # Mask token safely: expose only leading digits of bot id and trailing 3 chars
    if token_present and ":" in token:
        bot_id_part = token.split(":")[0]
        token_masked = f"{bot_id_part[:6]}...{token[-3:]}"
    elif token_present:
        token_masked = f"{token[:4]}...{token[-2:]}"
    else:
        token_masked = "Not Configured"

    # Mask chat ID safely
    if chat_present and len(configured_chat) >= 6:
        chat_masked = f"{configured_chat[:4]}***{configured_chat[-3:]}"
    elif chat_present:
        chat_masked = "***"
    else:
        chat_masked = "Not Configured"

    diagnostic: Dict[str, Any] = {
        "provider": "telegram",
        "enabled": bool(settings.TELEGRAM_ENABLED),
        "configured": settings.telegram_configured,
        "token_present": token_present,
        "token_masked": token_masked,
        "token_length": len(token) if token_present else 0,
        "chat_id_present": chat_present,
        "chat_id_masked": chat_masked,
        "api_reachable": False,
        "bot_info": None,
        "chat_verification": None,
        "status": "unconfigured" if not (token_present and chat_present) else "checking",
        "detail": ""
    }

    if not token_present:
        diagnostic["status"] = "missing_token"
        diagnostic["detail"] = "TELEGRAM_BOT_TOKEN is not configured in backend/.env."
        return diagnostic

    if not chat_present:
        diagnostic["status"] = "missing_chat_id"
        diagnostic["detail"] = "TELEGRAM_CHAT_ID is not configured in backend/.env."
        return diagnostic

    # Verify bot connectivity via getMe
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            me_resp = await client.get(f"https://api.telegram.org/bot{token}/getMe")
            if me_resp.status_code == 200 and me_resp.json().get("ok"):
                bot_data = me_resp.json().get("result", {})
                diagnostic["api_reachable"] = True
                diagnostic["bot_info"] = {
                    "id": bot_data.get("id"),
                    "is_bot": bot_data.get("is_bot", True),
                    "first_name": bot_data.get("first_name"),
                    "username": bot_data.get("username")
                }
            else:
                err = me_resp.json().get("description") if me_resp.headers.get("content-type", "").startswith("application/json") else f"HTTP {me_resp.status_code}"
                diagnostic["status"] = "invalid_token"
                diagnostic["detail"] = f"Telegram Bot API rejected token: {sanitize_telegram_token(err, token)}"
                return diagnostic

            # Verify chat ID via getChat
            chat_resp = await client.post(
                f"https://api.telegram.org/bot{token}/getChat",
                json={"chat_id": configured_chat}
            )
            if chat_resp.status_code == 200 and chat_resp.json().get("ok"):
                c_data = chat_resp.json().get("result", {})
                diagnostic["chat_verification"] = {
                    "verified": True,
                    "type": c_data.get("type"),
                    "first_name": c_data.get("first_name"),
                    "username": c_data.get("username")
                }
                diagnostic["status"] = "verified"
                diagnostic["detail"] = (
                    f"Telegram verified: Connected as @{diagnostic['bot_info'].get('username')} "
                    f"and confirmed chat ID {chat_masked} reachability."
                )
            else:
                c_err = chat_resp.json().get("description") if chat_resp.headers.get("content-type", "").startswith("application/json") else f"HTTP {chat_resp.status_code}"
                diagnostic["chat_verification"] = {
                    "verified": False,
                    "error": sanitize_telegram_token(c_err, token)
                }
                diagnostic["status"] = "chat_unreachable"
                bot_user = diagnostic["bot_info"].get("username", "your bot")
                diagnostic["detail"] = (
                    f"Bot token is valid (@{bot_user}), but chat ID verification failed: '{c_err}'. "
                    f"Please open Telegram, search for @{bot_user}, and send /start."
                )
    except Exception as exc:
        diagnostic["status"] = "network_error"
        diagnostic["detail"] = f"Could not reach Telegram Bot API: {sanitize_telegram_token(str(exc), token)}"

    return diagnostic


async def dispatch_telegram(
    chat_id: Optional[str] = None,
    message: str = "",
    html_message: Optional[str] = None,
    token: Optional[str] = None
) -> Dict[str, Any]:
    """
    Sends an instant notification via the official Telegram Bot API (sendMessage).
    Never exposes or logs the Bot Token.
    Returns delivered status only when Telegram API confirms success (ok: true).
    """
    bot_token = (token or settings.TELEGRAM_BOT_TOKEN or "").strip()
    
    # Priority resolution for target chat ID
    if is_valid_telegram_chat_id(chat_id):
        target_chat_id = str(chat_id).strip()
    elif is_valid_telegram_chat_id(getattr(settings, "TELEGRAM_CHAT_ID", None)):
        target_chat_id = str(settings.TELEGRAM_CHAT_ID).strip()
    else:
        target_chat_id = (chat_id or getattr(settings, "TELEGRAM_CHAT_ID", "") or "").strip()

    if not getattr(settings, "TELEGRAM_ENABLED", True):
        raise ValueError("Telegram notifications are disabled. Set TELEGRAM_ENABLED=true in backend/.env to enable.")

    is_placeholder_token = not bot_token or "PASTE_YOUR" in bot_token or bot_token == "your_telegram_bot_token"
    if is_placeholder_token:
        raise ValueError(
            "Telegram bot token not configured. Please set TELEGRAM_BOT_TOKEN in backend/.env with your BotFather token."
        )

    is_placeholder_chat = not target_chat_id or "PASTE_YOUR" in str(target_chat_id) or str(target_chat_id) in ["your_telegram_chat_id"]
    if is_placeholder_chat:
        raise ValueError(
            "Telegram Chat ID not configured. Please set TELEGRAM_CHAT_ID in backend/.env with your chat ID."
        )

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": str(target_chat_id),
        "text": html_message or message,
        "parse_mode": "HTML" if html_message else None,
        "disable_web_page_preview": True
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)

            # Fallback if HTML parsing fails on Telegram's side
            if resp.status_code == 400 and ("can't parse entities" in resp.text.lower() or "entity" in resp.text.lower()):
                logger.warning("Telegram HTML entity parse issue; retrying as clean plain text.")
                plain_payload = {
                    "chat_id": str(target_chat_id),
                    "text": message or re.sub(r'<[^>]+>', '', html_message or ""),
                    "disable_web_page_preview": True
                }
                resp = await client.post(url, json=plain_payload)

            resp_data = {}
            try:
                resp_data = resp.json()
            except Exception:
                pass

            if resp.status_code != 200 or not resp_data.get("ok"):
                raw_err = resp_data.get("description") or resp.text or f"HTTP {resp.status_code}"
                safe_err = sanitize_telegram_token(raw_err, bot_token)
                code = resp_data.get("error_code", resp.status_code)
                logger.error(f"Telegram API dispatch error [{code}]: {safe_err}")
                if code == 400 and "chat not found" in safe_err.lower():
                    raise Exception(
                        f"Telegram error [400]: Bad Request: chat not found. "
                        f"Telegram bot cannot message chat ID {target_chat_id} until the user initiates the chat. "
                        f"Please open Telegram, search for the bot, and send /start."
                    )
                raise Exception(f"Telegram error [{code}]: {safe_err}")

            result = resp_data.get("result", {})
            msg_id = result.get("message_id")
            msg_id_str = str(msg_id) if msg_id else f"TG-{uuid.uuid4().hex[:8]}"

            logger.info(f"Telegram message confirmed delivered: ID={msg_id_str}, chat={target_chat_id}")
            return {
                "provider": "telegram",
                "provider_message_id": msg_id_str,
                "status": "delivered",
                "simulated": False,
                "recipient": str(target_chat_id),
                "detail": f"Message confirmed delivered by Telegram Bot API (Message ID: {msg_id_str})."
            }

    except httpx.TimeoutException:
        logger.error("Telegram API request timed out (10s limit).")
        raise Exception("Telegram request timed out. Please check your network connection.")
    except httpx.HTTPError as he:
        safe_msg = sanitize_telegram_token(str(he), bot_token)
        logger.error(f"Telegram network HTTP error: {safe_msg}")
        raise Exception(f"Telegram network error: {safe_msg}")
    except ValueError:
        raise
    except Exception as e:
        safe_msg = sanitize_telegram_token(str(e), bot_token)
        logger.error(f"Telegram dispatch error: {safe_msg}")
        raise Exception(safe_msg)


async def dispatch_sms(to_number: str, message: str) -> Dict[str, Any]:

    """
    Sends an SMS notification via Twilio Programmable Messaging using the official
    Twilio Python SDK (Client.messages.create).
    Normalizes phone numbers to standard E.164.
    If disabled, missing credentials, or API error, raises a clear Exception rather
    than fabricating a simulated delivery.
    """
    norm_phone = normalize_phone_number(to_number)
    short_msg = (message[:157] + "...") if len(message) > 160 else message
    provider = settings.SMS_PROVIDER.lower()

    if provider == "fast2sms":
        if not settings.FAST2SMS_API_KEY:
            raise ValueError("Fast2SMS API key not configured. Set FAST2SMS_API_KEY in backend/.env for live transmission.")

        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {"authorization": settings.FAST2SMS_API_KEY}
        clean_num = norm_phone.replace("+", "").replace("-", "").replace(" ", "")
        data = {
            "route": "q",
            "message": short_msg,
            "numbers": clean_num
        }
        if settings.FAST2SMS_DLT_TE_ID:
            data["route"] = "dlt"
            data["dlt_te_id"] = settings.FAST2SMS_DLT_TE_ID

        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(url, data=data, headers=headers)
            if resp.status_code != 200:
                raise Exception(f"Fast2SMS error {resp.status_code}: {resp.text}")
            resp_data = {}
            try:
                resp_data = resp.json()
            except Exception:
                pass
            msg_id = resp_data.get("request_id") or f"F2S-{uuid.uuid4().hex[:8]}"
            logger.info(f"Fast2SMS message dispatched: ID={msg_id}, recipient={norm_phone}")
            return {
                "provider": "fast2sms",
                "provider_message_id": msg_id,
                "status": "sent",
                "simulated": False,
                "recipient": norm_phone,
                "detail": "SMS submitted to Fast2SMS carrier gateway."
            }

    else:  # Twilio Programmable Messaging via Official Twilio Python SDK
        twilio_setting = getattr(settings, "TWILIO_ENABLED", None)
        if twilio_setting is not None:
            is_enabled = bool(twilio_setting)
        else:
            is_enabled = bool(getattr(settings, "SMS_ENABLED", False))

        if not is_enabled:
            raise ValueError("Twilio SMS is disabled. Set TWILIO_ENABLED=true in backend/.env to enable SMS notifications.")

        account_sid = settings.TWILIO_ACCOUNT_SID
        auth_token = settings.TWILIO_AUTH_TOKEN
        from_number = settings.TWILIO_FROM_NUMBER
        messaging_service_sid = settings.TWILIO_MESSAGING_SERVICE_SID

        is_placeholder_sid = not account_sid or not account_sid.startswith("AC") or "xxxxxxxx" in account_sid
        is_placeholder_token = not auth_token or auth_token == "your_twilio_auth_token_here" or "your_twilio" in auth_token or auth_token.strip() == ""
        has_valid_sender = bool((from_number and from_number != "+15551234567") or messaging_service_sid)

        if is_placeholder_sid or is_placeholder_token or not has_valid_sender:
            missing_items = []
            if is_placeholder_sid:
                missing_items.append("TWILIO_ACCOUNT_SID")
            if is_placeholder_token:
                missing_items.append("TWILIO_AUTH_TOKEN")
            if not has_valid_sender:
                missing_items.append("TWILIO_FROM_NUMBER")
            raise ValueError(
                f"Twilio credentials not configured ({', '.join(missing_items)}). "
                "Please configure valid credentials in backend/.env."
            )

        if not norm_phone:
            raise ValueError("Recipient phone number not provided. Please set TWILIO_TO_NUMBER in backend/.env or configure your mobile number.")

        def _send_twilio_sync():
            client = Client(account_sid, auth_token)
            kwargs = {
                "to": norm_phone,
                "body": short_msg,
            }
            if from_number:
                kwargs["from_"] = from_number
            elif messaging_service_sid:
                kwargs["messaging_service_sid"] = messaging_service_sid
            return client.messages.create(**kwargs)

        try:
            loop = asyncio.get_event_loop()
            msg = await loop.run_in_executor(None, _send_twilio_sync)
        except TwilioRestException as tw_err:
            code = getattr(tw_err, "code", getattr(tw_err, "status", "ERROR"))
            msg_str = getattr(tw_err, "msg", str(tw_err))
            logger.error(f"Twilio API error [{code}]: {msg_str}")
            raise Exception(f"Twilio error [{code}]: {msg_str}")
        except Exception as e:
            logger.error(f"Twilio dispatch error: {e}")
            raise e

        sid = getattr(msg, "sid", None)
        raw_status = getattr(msg, "status", "queued") or "queued"
        err_code = getattr(msg, "error_code", None)
        err_message = getattr(msg, "error_message", None)

        if err_code:
            raise Exception(f"Twilio error [{err_code}]: {err_message}")
        if raw_status in ["failed", "undelivered"]:
            raise Exception(f"Twilio message delivery failed with status: {raw_status}")

        logger.info(f"Twilio SMS accepted: SID={sid}, status={raw_status}, recipient={norm_phone}")
        return {
            "provider": "twilio",
            "provider_message_id": sid,
            "status": raw_status,
            "simulated": False,
            "recipient": norm_phone,
            "detail": f"SMS submitted to Twilio API. Status: {raw_status}. SID: {sid}"
        }


# ==============================================================================
# 5. Pluggable Service with Common Interface, Retries & Logging
# ==============================================================================

async def send_with_retries(delivery_fn, max_retries: int = 3):
    last_err = None
    for attempt in range(1, max_retries + 1):
        try:
            provider_result = await delivery_fn()
            return True, provider_result, None, attempt
        except ValueError as ve:
            # Configuration/validation errors: fail immediately without retry backoff delay
            return False, "telegram", sanitize_telegram_token(str(ve)), 1
        except Exception as e:
            last_err = sanitize_telegram_token(str(e))
            logger.warning(f"Notification attempt {attempt}/{max_retries} failed: {last_err}")
            # Client errors (HTTP 4xx like 400 chat not found, 401 unauthorized) will not succeed on retry
            if "Telegram error [4" in last_err or "Twilio error [4" in last_err or "chat not found" in last_err.lower():
                return False, "telegram", last_err, attempt
            if attempt < max_retries:
                await asyncio.sleep(2 ** (attempt - 1))
    return False, "unknown", last_err, max_retries


async def send(
    user: User,
    title: str,
    message: str,
    channel: str = "all",  # 'email', 'web_push', 'telegram', 'sms', 'all'
    metadata: Optional[Dict[str, Any]] = None,
    db: Optional[Session] = None,
    alert_id: Optional[int] = None,
    repeat_count: int = 1
) -> Dict[str, Any]:
    """
    Common notification interface:
    Dispatches to Email (Primary), Web Push, and Telegram Bot API according to user settings and channel.
    Logs each send attempt into notifications_log with retries up to 3 times.
    """
    results = {}
    metadata = metadata or {}

    # Extract food name and next reminder if available, with alert lookup fallback
    food_name = metadata.get("food_name")
    next_rem = metadata.get("next_reminder")
    if db and alert_id and (not food_name or not next_rem):
        try:
            from app.models import Alert
            alert_obj = db.query(Alert).filter(Alert.id == alert_id).first()
            if alert_obj:
                if not food_name and alert_obj.food_item:
                    food_name = alert_obj.food_item.name
                if not next_rem and alert_obj.next_reminder_at:
                    next_rem = alert_obj.next_reminder_at
        except Exception:
            pass

    next_rem_dt = None
    if isinstance(next_rem, datetime):
        next_rem_dt = next_rem
    elif isinstance(next_rem, str):
        try:
            next_rem_dt = datetime.fromisoformat(next_rem.replace("Z", "+00:00"))
        except Exception:
            pass

    def _safe_err(err: Optional[str]) -> Optional[str]:
        if not err:
            return None
        return sanitize_telegram_token(str(err))[:500]

    def _safe_record_notification_log(target_db: Optional[Session], entry: NotificationLog) -> None:
        if not target_db:
            return
        try:
            target_db.add(entry)
            target_db.commit()
        except Exception as exc:
            try:
                target_db.rollback()
            except Exception:
                pass
            logger.warning(f"Could not persist notification log to database (non-fatal): {exc}")

    # 1. EMAIL CHANNEL
    should_send_email = (channel in ["email", "all"]) and user.email_notifications_enabled
    if should_send_email and user.email:
        html_content = render_alert_email_html(title, message, metadata)

        async def _do_email():
            return await dispatch_email(user.email, title, html_content)

        success, provider, err, attempts = await send_with_retries(_do_email, max_retries=3)
        provider_name = str(provider)
        is_sim = "simulated" in provider_name.lower() or not (settings.SMTP_USER and settings.SMTP_PASSWORD)
        email_status = "simulated" if is_sim else ("accepted" if success else "failed")
        email_msg_id = f"SMTP-{uuid.uuid4().hex[:12].upper()}" if provider_name == "smtp" else f"{provider_name.upper()}-{uuid.uuid4().hex[:10].upper()}"

        results["email"] = {
            "success": success,
            "provider": provider_name,
            "provider_message_id": email_msg_id,
            "status": email_status,
            "attempts": attempts,
            "error": _safe_err(err)
        }

        if db:
            log_entry = NotificationLog(
                user_id=user.id,
                alert_id=alert_id,
                food_name=food_name,
                provider_message_id=email_msg_id,
                channel="email",
                provider=provider_name,
                recipient=user.email,
                title=title,
                message=message,
                status=email_status,
                error_message=_safe_err(err),
                attempts=attempts,
                metadata_json=json.dumps(metadata),
                created_at=datetime.utcnow(),
                sent_at=datetime.utcnow() if success else None,
                next_reminder_at=next_rem_dt
            )
            _safe_record_notification_log(db, log_entry)

    # 2. WEB PUSH CHANNEL
    should_send_push = (channel in ["web_push", "all"]) and user.push_notifications_enabled and settings.WEB_PUSH_ENABLED
    if should_send_push and user.push_subscription:
        async def _do_push():
            return await dispatch_web_push(user.push_subscription, title, message, metadata, user=user, db=db)

        success, provider, err, attempts = await send_with_retries(_do_push, max_retries=3)
        provider_name = str(provider)
        is_sim = "simulated" in provider_name.lower()
        push_status = "simulated" if is_sim else ("accepted" if success else "failed")
        push_msg_id = f"VAPID-{uuid.uuid4().hex[:14].upper()}"

        results["web_push"] = {
            "success": success,
            "provider": provider_name,
            "provider_message_id": push_msg_id,
            "status": push_status,
            "attempts": attempts,
            "error": _safe_err(err)
        }

        if db:
            log_entry = NotificationLog(
                user_id=user.id,
                alert_id=alert_id,
                food_name=food_name,
                provider_message_id=push_msg_id,
                channel="web_push",
                provider=provider_name,
                recipient=user.push_subscription[:100] if user.push_subscription else None,
                title=title,
                message=message,
                status=push_status,
                error_message=_safe_err(err),
                attempts=attempts,
                metadata_json=json.dumps(metadata),
                created_at=datetime.utcnow(),
                sent_at=datetime.utcnow() if success else None,
                next_reminder_at=next_rem_dt
            )
            _safe_record_notification_log(db, log_entry)

    # 3. TELEGRAM BOT CHANNEL (Primary Mobile Notification Provider - Replaces Twilio)
    # Explicit "telegram" or "sms" channel always executes (for tests, manual triggers, and repeating jobs).
    # "all" channel checks user preference and Telegram enabled setting.
    is_tg_active = getattr(settings, "TELEGRAM_ENABLED", True)
    is_twilio_active = bool(getattr(settings, "TWILIO_ENABLED", False))

    user_tg_pref = getattr(user, "telegram_notifications_enabled", None)
    if user_tg_pref is None:
        user_tg_pref = getattr(user, "sms_notifications_enabled", None)
    if user_tg_pref is None:
        user_tg_pref = getattr(user, "sms_enabled", True)

    should_send_telegram = (channel in ["telegram", "sms"]) or (
        channel == "all" and bool(user_tg_pref) and bool(is_tg_active)
    )

    chat_id_to_use = resolve_telegram_chat_id(
        user=user,
        metadata=metadata,
        override_chat_id=metadata.get("chat_id") or metadata.get("telegram_chat_id")
    )

    if should_send_telegram:
        food_cat = metadata.get("category")
        alert_type = metadata.get("alert_type")
        severity = metadata.get("severity")
        days_left = metadata.get("days_left")
        temp_c = metadata.get("temperature")
        zone_name = metadata.get("zone_name")
        status_val = metadata.get("status")
        detection_time_val = metadata.get("detection_time")

        html_body = format_telegram_alert(
            title=title,
            message=message,
            food_name=food_name,
            category=food_cat,
            severity=severity,
            alert_type=alert_type,
            days_until_expiry=days_left,
            temp_c=temp_c,
            zone_name=zone_name,
            repeat_count=repeat_count,
            status=status_val,
            detection_time=detection_time_val,
            metadata=metadata
        )

        plain_body = format_sms_alert(
            title=title,
            message=message,
            food_name=food_name,
            category=food_cat,
            severity=severity,
            alert_type=alert_type,
            days_until_expiry=days_left,
            temp_c=temp_c,
            zone_name=zone_name,
            repeat_count=repeat_count,
            status=status_val,
            detection_time=detection_time_val
        )

        # Select mobile delivery mechanism:
        # If Telegram is requested, dispatch via Telegram Bot API.
        # If Twilio is active or channel is "sms", dispatch via dispatch_sms (Twilio / SMS).
        # Otherwise, dispatch via primary active provider (Telegram Bot API).
        if channel == "telegram":
            async def _do_mobile():
                res = dispatch_telegram(
                    chat_id=chat_id_to_use,
                    message=plain_body,
                    html_message=html_body
                )
                if asyncio.iscoroutine(res):
                    return await res
                return res
            success, res_or_prov, err, attempts = await send_with_retries(_do_mobile, max_retries=3)
        elif is_twilio_active or channel == "sms":
            phone_to_use = user.phone_number or getattr(settings, "TWILIO_TO_NUMBER", None) or getattr(settings, "SMS_TO_NUMBER", None)
            async def _do_mobile():
                res = dispatch_sms(phone_to_use, plain_body)
                if asyncio.iscoroutine(res):
                    return await res
                return res
            success, res_or_prov, err, attempts = await send_with_retries(_do_mobile, max_retries=3)
        else:
            # Active Notification Flow: Telegram Bot API
            async def _do_mobile():
                res = dispatch_telegram(
                    chat_id=chat_id_to_use,
                    message=plain_body,
                    html_message=html_body
                )
                if asyncio.iscoroutine(res):
                    return await res
                return res
            success, res_or_prov, err, attempts = await send_with_retries(_do_mobile, max_retries=3)

        if isinstance(res_or_prov, dict):
            provider_name = res_or_prov.get("provider", "telegram")
            provider_msg_id = res_or_prov.get("provider_message_id")
            raw_status = res_or_prov.get("status", "delivered" if success else "failed")
            is_simulated = res_or_prov.get("simulated", False)
            recipient_used = res_or_prov.get("recipient", chat_id_to_use or "Not Configured")
            detail_msg = res_or_prov.get("detail", "")
        else:
            provider_name = str(res_or_prov) if res_or_prov else "telegram"
            provider_msg_id = None
            raw_status = "delivered" if success else "failed"
            is_simulated = False
            recipient_used = chat_id_to_use or "Not Configured"
            detail_msg = ""

        # Status: delivered for Telegram on success, accepted/raw_status for SMS/Twilio, failed on error
        if success and provider_name == "twilio" and raw_status == "queued":
            final_status = "accepted"
        else:
            final_status = raw_status if success else "failed"

        mobile_result = {
            "success": success,
            "provider": provider_name,
            "provider_message_id": provider_msg_id,
            "status": final_status,
            "is_simulated": is_simulated,
            "recipient": str(recipient_used),
            "attempts": attempts,
            "detail": detail_msg,
            "formatted_message": plain_body,
            "repeat_count": repeat_count,
            "error": _safe_err(err)
        }

        # Route results and logs appropriately
        is_telegram_flow = (provider_name == "telegram") or (channel == "telegram")
        if is_telegram_flow:
            results["telegram"] = mobile_result
            results["sms"] = mobile_result  # Backwards compatibility alias
            channel_for_log = "telegram"
        else:
            results["sms"] = mobile_result
            channel_for_log = "sms"

        if db:
            log_entry = NotificationLog(
                user_id=user.id,
                alert_id=alert_id,
                food_name=food_name,
                provider_message_id=provider_msg_id,
                repeat_count=repeat_count,
                channel=channel_for_log,
                provider=provider_name,
                recipient=str(recipient_used),
                title=f"{title} ({channel_for_log.capitalize()} #{repeat_count})" if repeat_count > 1 else title,
                message=plain_body,
                status=final_status,
                error_message=_safe_err(err),
                attempts=attempts,
                metadata_json=json.dumps(metadata),
                created_at=datetime.utcnow(),
                sent_at=datetime.utcnow() if success else None,
                next_reminder_at=next_rem_dt
            )
            _safe_record_notification_log(db, log_entry)

    return results



async def send_daily_digest(user: User, items: List[Dict[str, Any]], db: Optional[Session] = None) -> Dict[str, Any]:
    """
    Sends the 8:00 AM daily digest email listing expiring foods.
    """
    if not (user.email and user.email_daily_digest and user.email_notifications_enabled):
        return {"status": "skipped"}

    subject = f"Smart Fridge Digest: {len(items)} item(s) need attention today"
    html_body = render_daily_digest_html(items)

    async def _do_digest():
        return await dispatch_email(user.email, subject, html_body)

    success, provider, err, attempts = await send_with_retries(_do_digest, max_retries=3)

    if db:
        digest_log = NotificationLog(
            user_id=user.id,
            channel="email",
            provider=provider,
            recipient=user.email,
            title=subject,
            message=f"Daily digest with {len(items)} expiring items",
            status="sent" if success else "failed",
            error_message=err,
            attempts=attempts,
            sent_at=datetime.utcnow() if success else None
        )
        try:
            db.add(digest_log)
            db.commit()
        except Exception as exc:
            try:
                db.rollback()
            except Exception:
                pass
            logger.warning(f"Could not persist daily digest log (non-fatal): {exc}")

    return {"success": success, "provider": provider}
