import random
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Zone, SensorReading

logger = logging.getLogger(__name__)

def update_sensor_readings(db: Session):
    """
    Performs a realistic random walk for each refrigerator zone sensor reading.
    Updates Zone current stats and appends to SensorReading table.
    """
    zones = db.query(Zone).all()
    if not zones:
        return

    for zone in zones:
        # Small random walk
        temp_delta = random.uniform(-0.25, 0.25)
        hum_delta = random.uniform(-1.0, 1.0)

        # Zone-specific boundary centers
        if zone.code == "freezer":
            base_temp = -17.5
            base_hum = 50.0
            new_temp = round(max(-22.0, min(-14.0, zone.current_temp + temp_delta)), 1)
            new_hum = round(max(40.0, min(65.0, zone.current_humidity + hum_delta)), 1)
        elif zone.code == "vegetable_drawer":
            new_temp = round(max(3.5, min(8.5, zone.current_temp + temp_delta)), 1)
            new_hum = round(max(75.0, min(95.0, zone.current_humidity + hum_delta)), 1)
        elif zone.code == "bottom_shelf":
            new_temp = round(max(1.0, min(4.5, zone.current_temp + temp_delta)), 1)
            new_hum = round(max(60.0, min(85.0, zone.current_humidity + hum_delta)), 1)
        elif zone.code == "top_shelf":
            new_temp = round(max(2.5, min(6.0, zone.current_temp + temp_delta)), 1)
            new_hum = round(max(55.0, min(78.0, zone.current_humidity + hum_delta)), 1)
        else: # middle shelf
            new_temp = round(max(2.0, min(5.0, zone.current_temp + temp_delta)), 1)
            new_hum = round(max(58.0, min(80.0, zone.current_humidity + hum_delta)), 1)

        # Calculate Health Score (100 is optimal)
        score = 100
        if new_temp < zone.target_temp_min:
            score -= int((zone.target_temp_min - new_temp) * 15)
        elif new_temp > zone.target_temp_max:
            score -= int((new_temp - zone.target_temp_max) * 15)

        if new_hum < zone.target_humidity_min:
            score -= int((zone.target_humidity_min - new_hum) * 1.5)
        elif new_hum > zone.target_humidity_max:
            score -= int((new_hum - zone.target_humidity_max) * 1.5)

        score = max(10, min(100, score))
        status = "normal" if score >= 85 else "warning" if score >= 65 else "critical"

        # Update Zone
        zone.current_temp = new_temp
        zone.current_humidity = new_hum
        zone.health_score = score
        zone.status = status

        # Record sensor reading
        reading = SensorReading(
            zone_id=zone.id,
            temperature=new_temp,
            humidity=new_hum,
            timestamp=datetime.utcnow()
        )
        db.add(reading)

    db.commit()
    logger.debug("Sensor simulator: updated readings for all zones.")
