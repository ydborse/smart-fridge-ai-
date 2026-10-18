from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FoodItem, Zone, SensorReading, Alert, User
from app.schemas import DashboardSummaryOut
from app.routers.foods import serialize_food
from app.security import get_current_user

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    now = datetime.utcnow()

    # Active food items
    foods = db.query(FoodItem).filter(
        FoodItem.user_id == current_user.id,
        FoodItem.is_used == False,
        FoodItem.is_discarded == False
    ).all()

    total_items = len(foods)
    fresh_items = 0
    expiring_soon_items = 0
    expired_items = 0

    expiring_soon_list = []
    
    for f in foods:
        diff_days = (f.expiry_date - now).total_seconds() / 86400.0
        is_expired = diff_days < 0 or f.freshness_status in ["Expired", "Rotten"]

        if is_expired:
            expired_items += 1
        elif diff_days <= 3 or f.freshness_status in ["Expiring Soon", "Ripe", "Overripe"]:
            expiring_soon_items += 1
            expiring_soon_list.append(f)
        else:
            fresh_items += 1

    # Sort expiring soon by expiry_date asc
    expiring_soon_list.sort(key=lambda x: x.expiry_date)
    serialized_expiring = [serialize_food(f) for f in expiring_soon_list[:6]]

    # Recently added items
    recently_added = sorted(foods, key=lambda x: x.added_at, reverse=True)[:6]
    serialized_recent = [serialize_food(f) for f in recently_added]

    # Zones overview
    zones = db.query(Zone).all()
    zone_stats = []
    for z in zones:
        z_count = len([f for f in foods if f.zone_id == z.id])
        zone_stats.append({
            "id": z.id,
            "name": z.name,
            "code": z.code,
            "temperature": z.current_temp,
            "humidity": z.current_humidity,
            "health_score": z.health_score,
            "status": z.status,
            "item_count": z_count
        })

    # 24h Temperature line chart points (grouped per hour for Top, Middle, Bottom shelves)
    cutoff = now - timedelta(hours=24)
    readings = db.query(SensorReading).filter(SensorReading.timestamp >= cutoff).order_by(SensorReading.timestamp.asc()).all()

    # Map zones by code
    shelf_zone_ids = {z.code: z.id for z in zones}
    
    # Bucket by timestamp string "%H:00"
    hour_buckets = {}
    for r in readings:
        h_key = r.timestamp.strftime("%H:00")
        if h_key not in hour_buckets:
            hour_buckets[h_key] = {"time": h_key}
        
        if r.zone_id == shelf_zone_ids.get("top_shelf"):
            hour_buckets[h_key]["top_shelf"] = r.temperature
            hour_buckets[h_key]["top_hum"] = r.humidity
        elif r.zone_id == shelf_zone_ids.get("middle_shelf"):
            hour_buckets[h_key]["middle_shelf"] = r.temperature
            hour_buckets[h_key]["middle_hum"] = r.humidity
        elif r.zone_id == shelf_zone_ids.get("bottom_shelf"):
            hour_buckets[h_key]["bottom_shelf"] = r.temperature
            hour_buckets[h_key]["bottom_hum"] = r.humidity
        elif r.zone_id == shelf_zone_ids.get("vegetable_drawer"):
            hour_buckets[h_key]["veg_drawer"] = r.temperature
            hour_buckets[h_key]["veg_hum"] = r.humidity
        elif r.zone_id == shelf_zone_ids.get("freezer"):
            hour_buckets[h_key]["freezer"] = r.temperature

    temp_chart_data = list(hour_buckets.values())

    # Generate Smart "Today's Insights"
    insights = []
    if expired_items > 0:
        insights.append(f"⚠️ {expired_items} item{'s need' if expired_items!=1 else ' needs'} immediate removal to keep your fridge hygienic.")
    if expiring_soon_items > 0:
        insights.append(f"⏰ {expiring_soon_items} item{'s are' if expiring_soon_items!=1 else ' is'} expiring within 3 days. Check recipe ideas to use them up!")
    
    # Check ethylene gas in insights
    ethylene_conflicts = [z["name"] for z in zone_stats if any("Ethylene" in a.title for a in db.query(Alert).filter(Alert.zone_id == z["id"], Alert.is_read == False).all())]
    if ethylene_conflicts:
        insights.append(f"🍎 Ethylene gas alert in {', '.join(ethylene_conflicts)}. Separate fruits from leafy greens.")
    else:
        insights.append("🌿 Ethylene gas levels are well balanced across all shelves.")

    avg_health = int(sum(z.health_score for z in zones) / max(1, len(zones)))
    insights.append(f"❄️ Refrigerator digital twin running smoothly with a {avg_health}% overall health index.")

    # Unread alerts
    unread_count = db.query(Alert).filter(Alert.user_id == current_user.id, Alert.is_read == False).count()

    return {
        "stats": {
            "total_items": total_items,
            "fresh_items": fresh_items,
            "expiring_soon_items": expiring_soon_items,
            "expired_items": expired_items
        },
        "insights": insights,
        "expiring_soon": serialized_expiring,
        "recently_added": serialized_recent,
        "zone_stats": zone_stats,
        "temperature_history_24h": temp_chart_data,
        "unread_alerts_count": unread_count
    }
