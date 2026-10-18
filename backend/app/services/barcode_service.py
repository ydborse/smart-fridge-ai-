import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import httpx
from sqlalchemy.orm import Session
from app.models import BarcodeCache, ShelfLifeDefault, Zone

logger = logging.getLogger(__name__)

OFF_API_URL = "https://world.openfoodfacts.org/api/v2/product/{barcode}.json"
USER_AGENT = "SmartFridgeApp/1.0 (contact@smartfridge.local)"

CATEGORY_SHELF_LIFE = {
    "milk": (5, "bottom_shelf"),
    "dairy": (7, "middle_shelf"),
    "curd": (7, "middle_shelf"),
    "yogurt": (10, "middle_shelf"),
    "paneer": (7, "middle_shelf"),
    "cheese": (14, "middle_shelf"),
    "butter": (30, "top_shelf"),
    "egg": (21, "middle_shelf"),
    "juice": (7, "top_shelf"),
    "beverage": (14, "top_shelf"),
    "meat": (3, "bottom_shelf"),
    "fish": (2, "bottom_shelf"),
    "sauce": (60, "top_shelf"),
    "condiment": (90, "top_shelf"),
    "bread": (5, "top_shelf"),
    "snack": (30, "top_shelf")
}

def guess_shelf_life_and_zone(name: str, categories: str, db: Session):
    lower_text = f"{name} {categories}".lower()
    
    # Check DB shelf_life_defaults first
    for item in db.query(ShelfLifeDefault).all():
        if item.item_name.lower() in lower_text:
            return item.typical_shelf_life_days, item.recommended_zone_code

    for keyword, (days, zone_code) in CATEGORY_SHELF_LIFE.items():
        if keyword in lower_text:
            return days, zone_code

    return 7, "middle_shelf"


async def lookup_barcode(barcode: str, db: Session) -> Dict[str, Any]:
    """
    Looks up product by barcode in cache or Open Food Facts API.
    """
    clean_code = barcode.strip()
    
    # 1. Check local cache in DB
    cached = db.query(BarcodeCache).filter(BarcodeCache.barcode == clean_code).first()
    if cached:
        shelf_days, rec_zone_code = guess_shelf_life_and_zone(cached.product_name, cached.category or "", db)
        rec_zone = db.query(Zone).filter(Zone.code == rec_zone_code).first() or db.query(Zone).first()
        
        return {
            "barcode": cached.barcode,
            "name": cached.product_name,
            "brand": cached.brand,
            "category": cached.category or "Packaged Food",
            "image_url": cached.image_url,
            "quantity_str": cached.quantity_str,
            "nutri_score": cached.nutri_score,
            "default_shelf_life_days": shelf_days,
            "suggested_expiry_date": datetime.utcnow() + timedelta(days=shelf_days),
            "suggested_zone_id": rec_zone.id if rec_zone else 1,
            "suggested_zone_name": rec_zone.name if rec_zone else "Middle Shelf"
        }

    # 2. Call Open Food Facts API
    url = OFF_API_URL.format(barcode=clean_code)
    product_data = None
    
    try:
        async with httpx.AsyncClient(timeout=8.0, headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == 1 and "product" in data:
                    product_data = data["product"]
    except Exception as e:
        logger.warning(f"Open Food Facts lookup failed: {e}")

    if product_data:
        prod_name = (
            product_data.get("product_name") or
            product_data.get("product_name_en") or
            product_data.get("generic_name") or
            f"Product {clean_code}"
        )
        brand = product_data.get("brands")
        category = product_data.get("categories") or "Packaged"
        img_url = product_data.get("image_front_url") or product_data.get("image_url")
        quantity = product_data.get("quantity")
        nutri_score = product_data.get("nutriscore_grade")
        
        # Save to cache
        cache_entry = BarcodeCache(
            barcode=clean_code,
            product_name=prod_name,
            brand=brand,
            category=category,
            image_url=img_url,
            quantity_str=quantity,
            nutri_score=nutri_score,
            raw_data=json.dumps(product_data)[:4000]
        )
        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)
    else:
        # Mock/fallback for barcodes not found on Open Food Facts (e.g. sample items)
        mock_names = {
            "8901030382725": ("Amul Taaza Homogenised Toned Milk", "Amul", "Dairy / Milk", "1 L"),
            "8901262010052": ("Mother Dairy Classic Curd", "Mother Dairy", "Dairy / Curd", "400 g"),
            "8901491101835": ("Britannia Fresh Paneer", "Britannia", "Dairy / Paneer", "200 g"),
            "7622201736209": ("Oreo Vanilla Creme Biscuits", "Cadbury", "Packaged Snacks", "120 g"),
            "8901058852460": ("Tropicana 100% Orange Juice", "Tropicana", "Beverages / Juice", "1 L")
        }
        if clean_code in mock_names:
            name, brand, cat, qty = mock_names[clean_code]
        else:
            name = f"Packaged Food Item #{clean_code[-4:] if len(clean_code)>=4 else clean_code}"
            brand = "Generic Brand"
            cat = "Packaged Food"
            qty = "1 pack"

        cache_entry = BarcodeCache(
            barcode=clean_code,
            product_name=name,
            brand=brand,
            category=cat,
            image_url=None,
            quantity_str=qty,
            nutri_score="b",
            raw_data="{}"
        )
        db.add(cache_entry)
        db.commit()
        db.refresh(cache_entry)

    shelf_days, rec_zone_code = guess_shelf_life_and_zone(cache_entry.product_name, cache_entry.category or "", db)
    rec_zone = db.query(Zone).filter(Zone.code == rec_zone_code).first() or db.query(Zone).first()

    return {
        "barcode": cache_entry.barcode,
        "name": cache_entry.product_name,
        "brand": cache_entry.brand,
        "category": cache_entry.category or "Packaged Food",
        "image_url": cache_entry.image_url,
        "quantity_str": cache_entry.quantity_str,
        "nutri_score": cache_entry.nutri_score,
        "default_shelf_life_days": shelf_days,
        "suggested_expiry_date": datetime.utcnow() + timedelta(days=shelf_days),
        "suggested_zone_id": rec_zone.id if rec_zone else 1,
        "suggested_zone_name": rec_zone.name if rec_zone else "Middle Shelf"
    }
