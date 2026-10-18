import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import User, FoodItem, Alert, Zone, ShelfLifeDefault
from app.services.alert_engine import evaluate_food_alerts, evaluate_compatibility_alerts

@pytest.fixture
def test_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    # Create dummy zone & user
    user = User(email="test@user.com", hashed_password="pw", full_name="Tester", alert_lead_days=2)
    db.add(user)
    zone1 = Zone(name="Middle Shelf", code="middle_shelf", current_temp=3.5, current_humidity=65.0)
    zone2 = Zone(name="Vegetable Drawer", code="vegetable_drawer", current_temp=5.0, current_humidity=85.0)
    db.add_all([zone1, zone2])
    db.commit()

    yield db
    db.close()

@pytest.mark.asyncio
async def test_packaged_food_expiry_rule(test_db):
    user = test_db.query(User).first()
    zone = test_db.query(Zone).first()
    now = datetime.utcnow()

    # Expired packaged food
    expired_item = FoodItem(
        user_id=user.id,
        name="Expired Milk",
        item_type="packaged",
        zone_id=zone.id,
        added_at=now - timedelta(days=6),
        expiry_date=now - timedelta(days=1),
        freshness_status="Fresh"
    )
    test_db.add(expired_item)
    test_db.commit()

    alerts = await evaluate_food_alerts(test_db, user)
    assert len(alerts) >= 1
    assert any("Expired / Remove Now" in a.alert_type for a in alerts)
    assert expired_item.freshness_status == "Expired"

@pytest.mark.asyncio
async def test_fruit_rotten_rule(test_db):
    user = test_db.query(User).first()
    zone = test_db.query(Zone).first()
    now = datetime.utcnow()

    rotten_fruit = FoodItem(
        user_id=user.id,
        name="Rotten Banana",
        item_type="fruit",
        zone_id=zone.id,
        added_at=now - timedelta(days=5),
        expiry_date=now + timedelta(days=1),
        freshness_status="Rotten"
    )
    test_db.add(rotten_fruit)
    test_db.commit()

    alerts = await evaluate_food_alerts(test_db, user)
    assert any("Spoiled / Remove Now" in a.title or "Expired" in a.alert_type for a in alerts)

@pytest.mark.asyncio
async def test_safety_override_rule(test_db):
    user = test_db.query(User).first()
    zone = test_db.query(Zone).first()
    now = datetime.utcnow()

    # Item in fridge for 10 days while typical shelf life is 5
    shelf_def = ShelfLifeDefault(
        item_name="strawberry",
        category="Fruits",
        typical_shelf_life_days=5,
        recommended_zone_code="top_shelf"
    )
    test_db.add(shelf_def)
    test_db.commit()

    overstayed_item = FoodItem(
        user_id=user.id,
        name="Strawberry",
        item_type="fruit",
        zone_id=zone.id,
        added_at=now - timedelta(days=10),
        expiry_date=now + timedelta(days=3),
        freshness_status="Fresh"
    )
    test_db.add(overstayed_item)
    test_db.commit()

    alerts = await evaluate_food_alerts(test_db, user)
    # Safety rule overrides status from Fresh to Expiring Soon
    assert overstayed_item.freshness_status == "Expiring Soon"
