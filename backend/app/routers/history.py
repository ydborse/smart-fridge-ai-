from datetime import datetime
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ActivityHistory, User
from app.security import get_current_user

router = APIRouter(prefix="/history", tags=["History & Analytics"])


@router.get("")
def get_activity_history(
    action: str = Query(
        None,
        pattern="^(added|used|discarded|expired|updated)$",
    ),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Fetch the selected user's activity records.
    query = db.query(ActivityHistory).filter(
        ActivityHistory.user_id == current_user.id
    )

    if action:
        query = query.filter(ActivityHistory.action == action)

    activities = (
        query.order_by(ActivityHistory.timestamp.desc())
        .limit(limit)
        .all()
    )

    # Use all of this user's activity records for lifetime statistics.
    all_acts = (
        db.query(ActivityHistory)
        .filter(ActivityHistory.user_id == current_user.id)
        .all()
    )

    used_acts = [a for a in all_acts if a.action == "used"]
    wasted_acts = [
        a for a in all_acts
        if a.action in ("discarded", "expired")
    ]

    added_count = sum(1 for a in all_acts if a.action == "added")
    used_count = len(used_acts)
    discarded_count = len(wasted_acts)

    used_cost = sum(a.estimated_cost or 0.0 for a in used_acts)
    wasted_cost = sum(a.estimated_cost or 0.0 for a in wasted_acts)

    # These are activity-record-based metrics, not total quantities
    # across different units such as kg, litres, and pieces.
    total_resolved = used_count + discarded_count

    efficiency_rate = (
        round(used_count / total_resolved * 100, 1)
        if total_resolved
        else 0.0
    )

    waste_rate = (
        round(discarded_count / total_resolved * 100, 1)
        if total_resolved
        else 0.0
    )

    # Build the most recent five calendar months dynamically.
    now = datetime.utcnow()
    months_data = []
    month_lookup = {}

    for offset in range(4, -1, -1):
        month_number = now.month - offset
        year = now.year

        while month_number < 1:
            month_number += 12
            year -= 1

        key = f"{year}-{month_number:02d}"
        entry = {
            "month": datetime(year, month_number, 1).strftime("%b"),
            "consumed": 0,
            "wasted": 0,
        }

        months_data.append(entry)
        month_lookup[key] = entry

    # Count actual consumption and waste records in those months.
    for activity in all_acts:
        if not activity.timestamp:
            continue

        month_key = activity.timestamp.strftime("%Y-%m")
        month_entry = month_lookup.get(month_key)

        if not month_entry:
            continue

        if activity.action == "used":
            month_entry["consumed"] += 1
        elif activity.action in ("discarded", "expired"):
            month_entry["wasted"] += 1

    return {
        "timeline": [
            {
                "id": a.id,
                "action": a.action,
                "food_item_name": a.food_item_name,
                "quantity": a.quantity,
                "unit": a.unit,
                "estimated_cost": a.estimated_cost,
                "timestamp": a.timestamp,
            }
            for a in activities
        ],
        "stats": {
            "total_added": added_count,
            "total_consumed": used_count,
            "total_wasted": discarded_count,
            "waste_rate_percent": waste_rate,
            "efficiency_rate_percent": efficiency_rate,
            "money_saved": round(used_cost, 2),
            "money_wasted": round(wasted_cost, 2),
        },
        "monthly_comparison": months_data,
    }