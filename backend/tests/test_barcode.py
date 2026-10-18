import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models import BarcodeCache, ShelfLifeDefault, Zone
from app.services.barcode_service import guess_shelf_life_and_zone, lookup_barcode

@pytest.fixture
def barcode_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()
    
    zone = Zone(name="Bottom Shelf", code="bottom_shelf", current_temp=2.0, current_humidity=70.0)
    db.add(zone)
    db.commit()
    yield db
    db.close()

def test_guess_shelf_life_and_zone(barcode_db):
    days, zone = guess_shelf_life_and_zone("Fresh Whole Milk", "Dairy / Beverage", barcode_db)
    assert days == 5
    assert zone == "bottom_shelf"

    days, zone = guess_shelf_life_and_zone("Natural Set Curd", "Dairy / Fermented", barcode_db)
    assert days == 7

@pytest.mark.asyncio
async def test_lookup_barcode_cached(barcode_db):
    entry = BarcodeCache(
        barcode="1234567890",
        product_name="Test Milk Carton",
        brand="DairyCo",
        category="Dairy / Milk",
        quantity_str="1 L"
    )
    barcode_db.add(entry)
    barcode_db.commit()

    res = await lookup_barcode("1234567890", barcode_db)
    assert res["name"] == "Test Milk Carton"
    assert res["brand"] == "DairyCo"
    assert res["default_shelf_life_days"] == 5
