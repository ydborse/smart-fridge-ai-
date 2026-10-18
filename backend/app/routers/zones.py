from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Zone, FoodItem, User
from app.security import get_current_user

router = APIRouter(prefix="/zones", tags=["Refrigerator Zones"])

ETHYLENE_PRODUCERS = {"apple", "banana", "tomato", "avocado"}
ETHYLENE_SENSITIVE = {"lettuce", "coriander", "capsicum", "strawberry", "spinach"}

@router.get("", response_model=List[Dict[str, Any]])
def get_zones(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    zones = db.query(Zone).all()
    results = []
    
    for z in zones:
        foods = db.query(FoodItem).filter(
            FoodItem.zone_id == z.id,
            FoodItem.user_id == current_user.id,
            FoodItem.is_used == False,
            FoodItem.is_discarded == False
        ).all()

        # Check compatibility in this zone
        producers = [f.name for f in foods if f.name.lower() in ETHYLENE_PRODUCERS]
        sensitive = [f.name for f in foods if f.name.lower() in ETHYLENE_SENSITIVE]
        has_conflict = len(producers) > 0 and len(sensitive) > 0

        results.append({
            "id": z.id,
            "name": z.name,
            "code": z.code,
            "target_temp_min": z.target_temp_min,
            "target_temp_max": z.target_temp_max,
            "target_humidity_min": z.target_humidity_min,
            "target_humidity_max": z.target_humidity_max,
            "current_temp": z.current_temp,
            "current_humidity": z.current_humidity,
            "health_score": z.health_score,
            "status": z.status,
            "description": z.description,
            "item_count": len(foods),
            "items": [{"id": f.id, "name": f.name, "category": f.category, "freshness_status": f.freshness_status} for f in foods],
            "compatibility_conflict": has_conflict,
            "producers": producers,
            "sensitive": sensitive
        })
    return results

@router.get("/{zone_id}")
def get_zone_detail(zone_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    zone = db.query(Zone).filter(Zone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")

    foods = db.query(FoodItem).filter(
        FoodItem.zone_id == zone.id,
        FoodItem.user_id == current_user.id,
        FoodItem.is_used == False,
        FoodItem.is_discarded == False
    ).all()

    return {
        "zone": zone,
        "items": foods
    }
