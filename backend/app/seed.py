import logging
from datetime import datetime, timedelta
import random
from app.config import settings
from app.database import SessionLocal, Base, engine
from app.models import (
    User, Zone, FoodItem, FoodImage, BarcodeCache, Alert,
    SensorReading, ShelfLifeDefault, ActivityHistory, NotificationLog
)
from app.security import get_password_hash
from app.migrations import run_migrations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def seed_database():
    Base.metadata.create_all(bind=engine)
    try:
        run_migrations()
    except Exception as e:
        logger.warning(f"Schema migration in seed_database: {e}")
    db = SessionLocal()

    # 1. Seed or retrieve Demo User
    demo_user = db.query(User).filter(User.email == "demo@smartfridge.com").first()
    if not demo_user:
        seed_phone = getattr(settings, "SMS_TO_NUMBER", None)
        demo_user = User(
            email="demo@smartfridge.com",
            hashed_password=get_password_hash("SmartFridge123!"),
            full_name="Alex Morgan",
            phone_number=seed_phone,
            email_notifications_enabled=True,
            push_notifications_enabled=True,
            sms_notifications_enabled=True,
            email_for_expiring=True,
            email_for_expired=True,
            email_daily_digest=True,
            push_for_expiring=True,
            push_for_expired=True,
            
            sms_for_critical=False,
            spoilage_reminder_enabled=True,
            spoilage_reminder_interval_minutes=120,
            alert_lead_days=2,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            audit_day="Sunday",
            audit_time="10:00",
            is_active=True
        )
        db.add(demo_user)
        db.commit()
        db.refresh(demo_user)
    elif demo_user.telegram_chat_id in ["554433221", "PASTE_YOUR_CHAT_ID_HERE", "your_telegram_chat_id"]:
        demo_user.telegram_chat_id = None
        db.commit()

    user = db.query(User).filter(User.email == "aaryajadhav370@gmail.com").first()
    if not user:
        user = User(
            email="aaryajadhav370@gmail.com",
            hashed_password=get_password_hash("SmartFridge123!"),
            full_name="Alex Morgan",
            phone_number=seed_phone,
            email_notifications_enabled=True,
            push_notifications_enabled=True,
            sms_notifications_enabled=True,
            email_for_expiring=True,
            email_for_expired=True,
            email_daily_digest=True,
            push_for_expiring=True,
            push_for_expired=True,
            
            sms_for_critical=False,
            spoilage_reminder_enabled=True,
            spoilage_reminder_interval_minutes=120,
            alert_lead_days=2,
            quiet_hours_start="22:00",
            quiet_hours_end="07:00",
            audit_day="Sunday",
            audit_time="10:00",
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info("Demo user created.")

    # 2. Seed Zones
    zone_data = [
        {
            "name": "Top Shelf",
            "code": "top_shelf",
            "target_temp_min": 2.0, "target_temp_max": 5.0,
            "target_humidity_min": 55.0, "target_humidity_max": 75.0,
            "current_temp": 3.8, "current_humidity": 66.5,
            "health_score": 94, "status": "normal",
            "description": "Ready-to-eat foods, yogurts, juices, and leftovers."
        },
        {
            "name": "Middle Shelf",
            "code": "middle_shelf",
            "target_temp_min": 2.0, "target_temp_max": 4.0,
            "target_humidity_min": 60.0, "target_humidity_max": 75.0,
            "current_temp": 3.2, "current_humidity": 65.0,
            "health_score": 96, "status": "normal",
            "description": "Stable cold temperature. Eggs, cheese, paneer, and tofu."
        },
        {
            "name": "Bottom Shelf",
            "code": "bottom_shelf",
            "target_temp_min": 1.0, "target_temp_max": 3.0,
            "target_humidity_min": 65.0, "target_humidity_max": 80.0,
            "current_temp": 2.1, "current_humidity": 72.0,
            "health_score": 98, "status": "normal",
            "description": "Coldest shelf. Fresh milk, meat, poultry, and seafood."
        },
        {
            "name": "Vegetable Drawer",
            "code": "vegetable_drawer",
            "target_temp_min": 4.0, "target_temp_max": 7.0,
            "target_humidity_min": 80.0, "target_humidity_max": 95.0,
            "current_temp": 5.4, "current_humidity": 88.0,
            "health_score": 91, "status": "normal",
            "description": "High humidity crisper for greens, herbs, and vegetables."
        },
        {
            "name": "Freezer",
            "code": "freezer",
            "target_temp_min": -20.0, "target_temp_max": -15.0,
            "target_humidity_min": 45.0, "target_humidity_max": 60.0,
            "current_temp": -18.2, "current_humidity": 51.0,
            "health_score": 99, "status": "normal",
            "description": "Deep freeze for frozen vegetables, ice cream, and meat."
        },
        {
            "name": "Left Door Shelf",
            "code": "door_shelf_left",
            "target_temp_min": 3.0, "target_temp_max": 6.5,
            "target_humidity_min": 50.0, "target_humidity_max": 70.0,
            "current_temp": 4.5, "current_humidity": 62.0,
            "health_score": 95, "status": "normal",
            "description": "Door compartments for condiments, sauces, salad dressings, jams, and butter."
        },
        {
            "name": "Right Door Shelf",
            "code": "door_shelf_right",
            "target_temp_min": 3.0, "target_temp_max": 6.5,
            "target_humidity_min": 50.0, "target_humidity_max": 70.0,
            "current_temp": 4.2, "current_humidity": 64.0,
            "health_score": 96, "status": "normal",
            "description": "Door storage for milk cartons, water bottles, and tall beverages."
        }
    ]

    zones_map = {}
    for z in zone_data:
        existing_zone = db.query(Zone).filter(Zone.code == z["code"]).first()
        if not existing_zone:
            existing_zone = Zone(**z)
            db.add(existing_zone)
            db.commit()
            db.refresh(existing_zone)
        zones_map[z["code"]] = existing_zone

    logger.info("Zones seeded.")

    # 3. Seed Shelf Life Defaults
    shelf_items = [
        ("apple", "Fruits", 21, "middle_shelf", True, False),
        ("banana", "Fruits", 5, "top_shelf", True, False),
        ("tomato", "Vegetables", 7, "middle_shelf", True, False),
        ("avocado", "Fruits", 6, "middle_shelf", True, False),
        ("strawberry", "Fruits", 5, "top_shelf", False, True),
        ("lettuce", "Vegetables", 7, "vegetable_drawer", False, True),
        ("coriander", "Vegetables", 5, "vegetable_drawer", False, True),
        ("capsicum", "Vegetables", 10, "vegetable_drawer", False, True),
        ("green chilli", "Vegetables", 14, "vegetable_drawer", False, False),
        ("carrot", "Vegetables", 28, "vegetable_drawer", False, False),
        ("lychee", "Fruits", 7, "middle_shelf", False, False),
        ("milk", "Dairy", 5, "bottom_shelf", False, False),
        ("curd", "Dairy", 7, "middle_shelf", False, False),
        ("paneer", "Dairy", 7, "middle_shelf", False, False),
        ("cheese", "Dairy", 14, "middle_shelf", False, False),
        ("yogurt", "Dairy", 10, "top_shelf", False, False),
        ("eggs", "Dairy", 21, "middle_shelf", False, False),
        ("chicken", "Meat/Seafood", 3, "bottom_shelf", False, False),
        ("juice", "Beverages", 10, "top_shelf", False, False)
    ]

    for name, cat, days, z_code, is_prod, is_sens in shelf_items:
        if not db.query(ShelfLifeDefault).filter(ShelfLifeDefault.item_name == name).first():
            db.add(ShelfLifeDefault(
                item_name=name,
                category=cat,
                typical_shelf_life_days=days,
                recommended_zone_code=z_code,
                is_ethylene_producer=is_prod,
                is_ethylene_sensitive=is_sens
            ))
    db.commit()

    # 4. Seed Barcode Cache
    barcode_items = [
        ("8901030382725", "Amul Taaza Homogenised Toned Milk", "Amul", "Dairy / Milk", None, "1 L", "a"),
        ("8901262010052", "Mother Dairy Classic Curd", "Mother Dairy", "Dairy / Curd", None, "400 g", "a"),
        ("8901491101835", "Britannia Fresh Paneer", "Britannia", "Dairy / Paneer", None, "200 g", "b"),
        ("7622201736209", "Oreo Vanilla Creme Biscuits", "Cadbury", "Packaged Snacks", None, "120 g", "d"),
        ("8901058852460", "Tropicana 100% Orange Juice", "Tropicana", "Beverages / Juice", None, "1 L", "b")
    ]
    for bc, name, br, cat, img, qty, nutri in barcode_items:
        if not db.query(BarcodeCache).filter(BarcodeCache.barcode == bc).first():
            db.add(BarcodeCache(
                barcode=bc,
                product_name=name,
                brand=br,
                category=cat,
                image_url=img,
                quantity_str=qty,
                nutri_score=nutri,
                raw_data="{}"
            ))
    db.commit()

    # 5. Seed Food Items (24 items in mixed states)
    now = datetime.utcnow()
    existing_food_count = db.query(FoodItem).filter(FoodItem.user_id == demo_user.id).count()

    if existing_food_count == 0:
        foods_data = [
            # Fresh items (12)
            ("Fresh Gala Apples", "Fruits", "fruit", "middle_shelf", 1.0, "kg", now - timedelta(days=2), now + timedelta(days=14), "Fresh", None, None, "fruit_scan", 4.5),
            ("Greek Yogurt Natural", "Dairy", "packaged", "top_shelf", 500, "g", now - timedelta(days=1), now + timedelta(days=8), "Fresh", "8901262010052", "Nestle", "barcode_scan", 3.2),
            ("Organic Farm Eggs", "Dairy", "packaged", "middle_shelf", 12, "pcs", now - timedelta(days=3), now + timedelta(days=15), "Fresh", None, "CountryFarm", "manual", 4.0),
            ("Crisp Orange Carrots", "Vegetables", "vegetable", "vegetable_drawer", 500, "g", now - timedelta(days=2), now + timedelta(days=20), "Fresh", None, None, "fruit_scan", 1.8),
            ("Spicy Green Chillies", "Vegetables", "vegetable", "vegetable_drawer", 200, "g", now - timedelta(days=1), now + timedelta(days=10), "Fresh", None, None, "fruit_scan", 1.2),
            ("Organic Firm Tofu", "Dairy", "packaged", "middle_shelf", 250, "g", now - timedelta(days=2), now + timedelta(days=12), "Fresh", None, "SoyaKing", "manual", 2.5),
            ("Tropicana 100% Orange Juice", "Beverages", "packaged", "top_shelf", 1.0, "L", now - timedelta(days=2), now + timedelta(days=6), "Fresh", "8901058852460", "Tropicana", "barcode_scan", 3.8),
            ("Sweet Green Peas", "Vegetables", "packaged", "freezer", 500, "g", now - timedelta(days=10), now + timedelta(days=80), "Fresh", None, "Safal", "manual", 2.0),
            ("Mixed Wild Berries", "Fruits", "packaged", "freezer", 400, "g", now - timedelta(days=8), now + timedelta(days=60), "Fresh", None, "DelMonte", "manual", 4.9),
            ("Sharp White Cheddar", "Dairy", "packaged", "middle_shelf", 200, "g", now - timedelta(days=4), now + timedelta(days=18), "Fresh", None, "Amul", "manual", 3.5),
            ("Pure Butter Salted", "Dairy", "packaged", "top_shelf", 500, "g", now - timedelta(days=5), now + timedelta(days=35), "Fresh", None, "Amul", "manual", 4.2),
            ("Unsweetened Almond Milk", "Dairy", "packaged", "bottom_shelf", 1.0, "L", now - timedelta(days=1), now + timedelta(days=9), "Fresh", None, "Silk", "manual", 3.0),
            
            # Expiring Soon items (6)
            ("Amul Taaza Toned Milk", "Dairy", "packaged", "bottom_shelf", 1.0, "L", now - timedelta(days=4), now + timedelta(days=1), "Expiring Soon", "8901030382725", "Amul", "barcode_scan", 1.5),
            ("Mother Dairy Classic Curd", "Dairy", "packaged", "middle_shelf", 400, "g", now - timedelta(days=5), now + timedelta(days=2), "Expiring Soon", "8901262010052", "Mother Dairy", "barcode_scan", 1.2),
            ("Britannia Fresh Paneer", "Dairy", "packaged", "middle_shelf", 200, "g", now - timedelta(days=5), now + timedelta(days=2), "Expiring Soon", "8901491101835", "Britannia", "barcode_scan", 2.2),
            ("Ripe Strawberries", "Fruits", "fruit", "top_shelf", 250, "g", now - timedelta(days=4), now + timedelta(days=1), "Ripe", None, None, "fruit_scan", 3.5),
            ("Golden Sweet Bananas", "Fruits", "fruit", "top_shelf", 6, "pcs", now - timedelta(days=4), now + timedelta(days=2), "Ripe", None, None, "fruit_scan", 2.0),
            ("Homemade Tomato Pasta", "Leftovers", "packaged", "top_shelf", 1, "pack", now - timedelta(days=2), now + timedelta(days=1), "Expiring Soon", None, None, "manual", 5.0),

            # Expired / Needs Removal (4)
            ("Green Capsicum", "Vegetables", "vegetable", "vegetable_drawer", 300, "g", now - timedelta(days=8), now - timedelta(days=1), "Overripe", None, None, "fruit_scan", 2.1),
            ("Fresh Coriander Bunch", "Vegetables", "vegetable", "vegetable_drawer", 100, "g", now - timedelta(days=7), now - timedelta(days=2), "Rotten", None, None, "fruit_scan", 0.8),
            ("Tender Chicken Breast", "Meat/Seafood", "packaged", "bottom_shelf", 500, "g", now - timedelta(days=4), now - timedelta(days=1), "Expired", None, "FreshToHome", "manual", 6.0),
            ("Vine Ripe Tomatoes", "Vegetables", "vegetable", "middle_shelf", 4, "pcs", now - timedelta(days=8), now - timedelta(days=1), "Rotten", None, None, "fruit_scan", 2.0),

            # Additional (2)
            ("Sweet Lychees", "Fruits", "fruit", "middle_shelf", 300, "g", now - timedelta(days=3), now + timedelta(days=4), "Fresh", None, None, "fruit_scan", 3.0),
            ("Madagascar Vanilla Ice Cream", "Packaged", "packaged", "freezer", 500, "ml", now - timedelta(days=12), now + timedelta(days=45), "Fresh", None, "Baskin", "manual", 5.5)
        ]

        for name, cat, itype, zcode, qty, unit, added, expiry, status, bcode, brand, src, cost in foods_data:
            zone = zones_map.get(zcode, zones_map["middle_shelf"])
            item = FoodItem(
                user_id=demo_user.id,
                name=name,
                category=cat,
                item_type=itype,
                zone_id=zone.id,
                quantity=qty,
                unit=unit,
                added_at=added,
                expiry_date=expiry,
                freshness_status=status,
                barcode=bcode,
                brand=brand,
                source=src,
                estimated_cost=cost
            )
            db.add(item)
        db.commit()
        logger.info("24 food items seeded.")

    # 6. Seed 24h Sensor History for all 5 Zones
    reading_count = db.query(SensorReading).count()
    if reading_count < 100:
        for hour in range(24, 0, -1):
            t_stamp = now - timedelta(hours=hour)
            for zcode, zone in zones_map.items():
                if zcode == "freezer":
                    base_t = -18.0 + random.uniform(-1.0, 1.0)
                    base_h = 51.0 + random.uniform(-3.0, 3.0)
                elif zcode == "vegetable_drawer":
                    base_t = 5.2 + random.uniform(-0.5, 0.5)
                    base_h = 88.0 + random.uniform(-3.0, 3.0)
                elif zcode == "bottom_shelf":
                    base_t = 2.2 + random.uniform(-0.4, 0.4)
                    base_h = 72.0 + random.uniform(-2.0, 2.0)
                elif zcode == "top_shelf":
                    base_t = 3.9 + random.uniform(-0.5, 0.5)
                    base_h = 66.0 + random.uniform(-2.5, 2.5)
                else:
                    base_t = 3.2 + random.uniform(-0.4, 0.4)
                    base_h = 65.0 + random.uniform(-2.0, 2.0)

                db.add(SensorReading(
                    zone_id=zone.id,
                    temperature=round(base_t, 1),
                    humidity=round(base_h, 1),
                    timestamp=t_stamp
                ))
        db.commit()
        logger.info("24 hours of sensor history seeded.")

    # 7. Seed Sample Alerts
    if db.query(Alert).filter(Alert.user_id == user.id).count() == 0:
        milk_item = db.query(FoodItem).filter(FoodItem.name.like("%Milk%")).first()
        coriander_item = db.query(FoodItem).filter(FoodItem.name.like("%Coriander%")).first()
        drawer_zone = zones_map["vegetable_drawer"]
        middle_zone = zones_map["middle_shelf"]

        alerts_to_add = [
            Alert(
                user_id=user.id,
                food_item_id=coriander_item.id if coriander_item else None,
                zone_id=drawer_zone.id,
                alert_type="Expired / Remove Now",
                severity="critical",
                title="Coriander Bunch Spoiled / Remove Now",
                message="This Coriander Bunch is no longer usable (Rotten). Remove it immediately to avoid spoilage spread.",
                channel_sent="email",
                created_at=now - timedelta(hours=2)
            ),
            Alert(
                user_id=user.id,
                food_item_id=milk_item.id if milk_item else None,
                zone_id=zones_map["bottom_shelf"].id,
                alert_type="Expiring Soon",
                severity="warning",
                title="Amul Taaza Milk Expiring Tomorrow",
                message="Amul Taaza Toned Milk expires in 1 day (tomorrow). Plan to use it soon!",
                channel_sent="web_push",
                created_at=now - timedelta(hours=5)
            ),
            Alert(
                user_id=user.id,
                zone_id=middle_zone.id,
                alert_type="Compatibility Warning",
                severity="warning",
                title="Ethylene Gas Warning in Middle Shelf",
                message="Ethylene producer (Fresh Gala Apples) is stored alongside sensitive items in Middle Shelf. Consider shifting apples to another shelf.",
                channel_sent="in_app",
                created_at=now - timedelta(hours=8)
            ),
            Alert(
                user_id=user.id,
                zone_id=zones_map["top_shelf"].id,
                alert_type="Temperature Warning",
                severity="warning",
                title="Door Ajar / Temperature Spike in Top Shelf",
                message="Top Shelf temperature reached 5.4°C briefly 12h ago. Returned to normal safe level (3.8°C).",
                is_read=True,
                channel_sent="in_app",
                created_at=now - timedelta(hours=12)
            )
        ]
        db.add_all(alerts_to_add)
        db.commit()
        logger.info("Sample alerts seeded.")

    # 8. Seed Activity History
    if db.query(ActivityHistory).filter(ActivityHistory.user_id == user.id).count() == 0:
        activities = [
            ActivityHistory(user_id=user.id, action="added", food_item_name="Amul Taaza Toned Milk", quantity=1.0, unit="L", estimated_cost=1.5, timestamp=now - timedelta(days=4)),
            ActivityHistory(user_id=user.id, action="used", food_item_name="Greek Yogurt Natural", quantity=250.0, unit="g", estimated_cost=1.6, timestamp=now - timedelta(days=2)),
            ActivityHistory(user_id=user.id, action="added", food_item_name="Ripe Strawberries", quantity=250.0, unit="g", estimated_cost=3.5, timestamp=now - timedelta(days=4)),
            ActivityHistory(user_id=user.id, action="discarded", food_item_name="Whole Wheat Bread", quantity=1.0, unit="pcs", estimated_cost=2.2, timestamp=now - timedelta(days=3)),
            ActivityHistory(user_id=user.id, action="added", food_item_name="Fresh Gala Apples", quantity=1.0, unit="kg", estimated_cost=4.5, timestamp=now - timedelta(days=2)),
            ActivityHistory(user_id=user.id, action="used", food_item_name="Cheddar Cheese Slice", quantity=100.0, unit="g", estimated_cost=1.8, timestamp=now - timedelta(hours=14)),
        ]
        db.add_all(activities)
        db.commit()
        logger.info("Activity history seeded.")

    # 9. Seed Notification Logs
    for target_u in [u for u in [user, demo_user] if u is not None]:
        if db.query(NotificationLog).filter(NotificationLog.user_id == target_u.id).count() == 0:
            logs = [
                NotificationLog(
                    user_id=target_u.id,
                    channel="email",
                    provider="smtp",
                    recipient=target_u.email,
                    title="Coriander Bunch Spoiled / Remove Now",
                    message="This Coriander Bunch is no longer usable (Rotten). Remove it immediately to avoid spoilage spread.",
                    status="sent",
                    attempts=1,
                    created_at=now - timedelta(hours=2),
                    sent_at=now - timedelta(hours=2)
                ),
                NotificationLog(
                    user_id=target_u.id,
                    channel="web_push",
                    provider="vapid",
                    recipient="PWA Web Push Client (Browser)",
                    title="Amul Taaza Milk Expiring Tomorrow",
                    message="Amul Taaza Toned Milk expires in 1 day (tomorrow). Plan to use it soon!",
                    status="sent",
                    attempts=1,
                    created_at=now - timedelta(hours=5),
                    sent_at=now - timedelta(hours=5)
                ),
                NotificationLog(
                    user_id=target_u.id,
                    channel="email",
                    provider="smtp",
                    recipient=target_u.email,
                    title="Smart Fridge Digest: 3 item(s) need attention today",
                    message="Daily digest with 3 expiring items sent to Alex Morgan",
                    status="sent",
                    attempts=1,
                    created_at=now - timedelta(days=1, hours=4),
                    sent_at=now - timedelta(days=1, hours=4)
                ),
            ]
            db.add_all(logs)
            db.commit()
    logger.info("Notification logs seeded.")

    db.close()
    logger.info("Database seeding complete!")

if __name__ == "__main__":
    seed_database()
