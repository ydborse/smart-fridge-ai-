from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Zone, SensorReading
from app.schemas import SensorReadingIn, SensorReadingOut

router = APIRouter(prefix="/sensors", tags=["Sensors & IoT"])

@router.get("/latest")
def get_latest_sensor_data(db: Session = Depends(get_db)):
    zones = db.query(Zone).all()
    return [
        {
            "zone_id": z.id,
            "zone_name": z.name,
            "zone_code": z.code,
            "temperature": z.current_temp,
            "humidity": z.current_humidity,
            "health_score": z.health_score,
            "status": z.status
        }
        for z in zones
    ]

@router.get("/history")
def get_sensor_history(
    hours: int = Query(24, ge=1, le=168),
    db: Session = Depends(get_db)
):
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    readings = db.query(SensorReading).filter(SensorReading.timestamp >= cutoff).order_by(SensorReading.timestamp.asc()).all()

    # Format for easy charting on frontend: group by timestamp or list of points
    zones = {z.id: z.name for z in db.query(Zone).all()}
    
    formatted = []
    for r in readings:
        formatted.append({
            "timestamp": r.timestamp.strftime("%H:%M"),
            "full_timestamp": r.timestamp.isoformat(),
            "zone_id": r.zone_id,
            "zone_name": zones.get(r.zone_id, "Unknown"),
            "temperature": r.temperature,
            "humidity": r.humidity
        })
    return formatted

@router.post("", response_model=Dict[str, Any])
def post_sensor_reading(
    reading_in: SensorReadingIn,
    db: Session = Depends(get_db)
):
    """
    Endpoint designed for real hardware sensors (MQTT / ESP32 / Arduino / Raspberry Pi)
    to post temperature & humidity readings.
    """
    zone = db.query(Zone).filter(Zone.code == reading_in.zone_code).first()
    if not zone:
        raise HTTPException(status_code=400, detail=f"Unknown zone code: {reading_in.zone_code}")

    zone.current_temp = reading_in.temperature
    zone.current_humidity = reading_in.humidity

    # Compute health score
    score = 100
    if zone.current_temp < zone.target_temp_min:
        score -= int((zone.target_temp_min - zone.current_temp) * 15)
    elif zone.current_temp > zone.target_temp_max:
        score -= int((zone.current_temp - zone.target_temp_max) * 15)

    if zone.current_humidity < zone.target_humidity_min:
        score -= int((zone.target_humidity_min - zone.current_humidity) * 1.5)
    elif zone.current_humidity > zone.target_humidity_max:
        score -= int((zone.current_humidity - zone.target_humidity_max) * 1.5)

    zone.health_score = max(10, min(100, score))
    zone.status = "normal" if score >= 85 else "warning" if score >= 65 else "critical"

    # Save to history
    reading = SensorReading(
        zone_id=zone.id,
        temperature=reading_in.temperature,
        humidity=reading_in.humidity,
        timestamp=datetime.utcnow()
    )
    db.add(reading)
    db.commit()

    return {
        "status": "success",
        "zone": zone.name,
        "current_temp": zone.current_temp,
        "current_humidity": zone.current_humidity,
        "health_score": zone.health_score
    }
