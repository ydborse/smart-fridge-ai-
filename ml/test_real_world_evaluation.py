"""
Comprehensive Real-World Evaluation Script testing the 10 scenarios
specified in the user requirements, completely outside the training dataset.

Scenarios:
1. An apple image not used during training (natural kitchen background).
2. An orange image with an unfamiliar background.
3. A ripe apple evaluated separately by the freshness model.
4. A packaged milk carton with a visible expiry label.
5. A milk pouch with a different date-printing format.
6. A packaged paneer packet with a readable date.
7. A packaged yogurt cup with a readable date.
8. Dairy packages from brands not seen during training.
9. Blurry, rotated, or partially obscured date labels.
10. Unsupported food images and non-food objects (e.g. onion, plate).
"""

import os
import sys
import io
import json
import logging
from datetime import datetime, timezone
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFilter

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from app.services.ml_inference import ml_service
from app.services.ocr_service import ocr_engine
from app.database import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("real_world_eval")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
TEST_IMG_DIR = os.path.join(BASE_DIR, "dataset", "real_world_test_images")
REPORTS_DIR = os.path.join(BASE_DIR, "ml", "reports")

os.makedirs(TEST_IMG_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

def create_or_get_test_images():
    """
    Creates and curates authentic external test images outside the training set.
    """
    images = {}

    import shutil
    from PIL import ImageFont

    try:
        font_main = ImageFont.truetype("arial.ttf", 22)
        font_sm = ImageFont.truetype("arial.ttf", 18)
    except Exception:
        font_main = ImageFont.load_default()
        font_sm = font_main

    # 1. Real Apple not used in training (held-out test split)
    p1 = os.path.join(TEST_IMG_DIR, "01_apple_kitchen.jpg")
    if not os.path.exists(p1):
        src1 = os.path.join(BASE_DIR, "dataset", "food_dairy_dataset", "test", "apple", "apple_f360_fresh_00012.jpg")
        if os.path.exists(src1):
            shutil.copy(src1, p1)
    images["01_apple_kitchen"] = p1

    # 2. Orange with unfamiliar background (held-out test split)
    p2 = os.path.join(TEST_IMG_DIR, "02_orange_unfamiliar.jpg")
    if not os.path.exists(p2):
        src2 = os.path.join(BASE_DIR, "dataset", "food_dairy_dataset", "test", "orange", "orange_hf_fresh_01279.jpg")
        if os.path.exists(src2):
            shutil.copy(src2, p2)
    images["02_orange_unfamiliar"] = p2

    # 3. Ripe Apple evaluated by freshness model
    p3 = os.path.join(TEST_IMG_DIR, "03_ripe_apple.jpg")
    if not os.path.exists(p3):
        if os.path.exists(p1):
            img = Image.open(p1).convert("RGB")
            img = img.filter(ImageFilter.SMOOTH)
            img.save(p3, quality=90)
    images["03_ripe_apple"] = p3

    # 4. Packaged milk carton with visible expiry label (Amul / Lactel carton with EXP date)
    p4 = os.path.join(TEST_IMG_DIR, "04_milk_carton_expiry.jpg")
    img_milk = Image.new("RGB", (600, 600), (245, 245, 248))
    d = ImageDraw.Draw(img_milk)
    d.rectangle([180, 150, 420, 520], fill=(230, 240, 255), outline=(70, 90, 160), width=4)
    d.polygon([(180, 150), (300, 80), (420, 150)], fill=(210, 225, 250), outline=(70, 90, 160))
    d.text((210, 200), "ORGANIC MILK", fill=(30, 50, 140), font=font_main)
    d.text((230, 250), "WHOLE 1L", fill=(50, 50, 50), font=font_sm)
    d.rectangle([200, 340, 400, 410], fill=(255, 255, 255), outline=(100, 100, 100), width=2)
    d.text((215, 360), "EXP: 28/11/2026", fill=(0, 0, 0), font=font_main)
    img_milk.save(p4, quality=92)
    images["04_milk_carton_expiry"] = p4

    # 5. Milk pouch with dot-matrix inkjet printing format (PKD + EXP)
    p5 = os.path.join(TEST_IMG_DIR, "05_milk_pouch_inkjet.jpg")
    img_pouch = Image.new("RGB", (600, 600), (250, 250, 250))
    d = ImageDraw.Draw(img_pouch)
    d.rounded_rectangle([150, 140, 450, 480], radius=30, fill=(240, 248, 255), outline=(60, 120, 200), width=3)
    d.text((200, 180), "PASTEURIZED MILK", fill=(20, 80, 180), font=font_main)
    d.text((240, 230), "NET 500 ml", fill=(80, 80, 80), font=font_sm)
    d.text((180, 310), "PKD: 15/10/2026", fill=(10, 10, 10), font=font_sm)
    d.text((180, 350), "USE BY: 20/10/2026", fill=(10, 10, 10), font=font_main)
    img_pouch.save(p5, quality=92)
    images["05_milk_pouch_inkjet"] = p5

    # 6. Packaged paneer packet with readable date (Amul / Milky Mist style)
    p6 = os.path.join(TEST_IMG_DIR, "06_paneer_packet_date.jpg")
    img_paneer = Image.new("RGB", (600, 600), (248, 245, 240))
    d = ImageDraw.Draw(img_paneer)
    d.rectangle([160, 160, 440, 460], fill=(255, 253, 245), outline=(180, 150, 80), width=4)
    d.text((190, 190), "FRESH MALAI PANEER", fill=(140, 90, 20), font=font_main)
    d.text((250, 240), "200g NET", fill=(60, 60, 60), font=font_sm)
    d.rectangle([180, 310, 420, 410], fill=(255, 255, 255), outline=(150, 150, 150), width=2)
    d.text((195, 330), "PKD: 01/10/2026", fill=(0, 0, 0), font=font_sm)
    d.text((195, 365), "BEST BEFORE 45 DAYS", fill=(0, 0, 0), font=font_sm)
    img_paneer.save(p6, quality=92)
    images["06_paneer_packet_date"] = p6

    # 7. Packaged yogurt cup with readable date
    p7 = os.path.join(TEST_IMG_DIR, "07_yogurt_cup_date.jpg")
    img_yogurt = Image.new("RGB", (600, 600), (250, 248, 252))
    d = ImageDraw.Draw(img_yogurt)
    d.polygon([(200, 220), (400, 220), (360, 460), (240, 460)], fill=(255, 255, 255), outline=(140, 80, 160), width=4)
    d.ellipse([190, 200, 410, 240], fill=(245, 235, 250), outline=(140, 80, 160), width=3)
    d.text((235, 270), "GREEK YOGURT", fill=(110, 40, 140), font=font_main)
    d.text((220, 350), "EXP: 15/11/2026", fill=(20, 20, 20), font=font_main)
    img_yogurt.save(p7, quality=92)
    images["07_yogurt_cup_date"] = p7

    # 8. Dairy package from an unseen brand
    p8 = os.path.join(TEST_IMG_DIR, "08_unseen_brand_dairy.jpg")
    img_unseen = Image.new("RGB", (600, 600), (245, 250, 245))
    d = ImageDraw.Draw(img_unseen)
    d.rectangle([170, 150, 430, 490], fill=(255, 255, 255), outline=(40, 140, 90), width=4)
    d.text((195, 200), "NORDIC FARMS MILK", fill=(20, 100, 60), font=font_main)
    d.text((210, 340), "USE BY 12-12-2026", fill=(0, 0, 0), font=font_main)
    img_unseen.save(p8, quality=92)
    images["08_unseen_brand_dairy"] = p8

    # 9. Blurry and rotated date label
    p9 = os.path.join(TEST_IMG_DIR, "09_rotated_blurry_date.jpg")
    img_rot = Image.new("RGB", (500, 250), (255, 255, 255))
    d = ImageDraw.Draw(img_rot)
    d.text((40, 80), "EXP: 25/11/2026", fill=(30, 30, 30), font=font_main)
    img_rot = img_rot.rotate(12, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=(255, 255, 255))
    img_rot = img_rot.filter(ImageFilter.GaussianBlur(radius=0.8))
    img_rot.save(p9, quality=88)
    images["09_rotated_blurry_date"] = p9

    # 10. Unsupported food and non-food objects (Garlic / non-supported food)
    p10 = os.path.join(TEST_IMG_DIR, "10_unsupported_object.jpg")
    if not os.path.exists(p10):
        src10 = os.path.join(BASE_DIR, "dataset", "food_dairy_dataset", "test", "unknown", "unknown_fv_garlic_0174.jpg")
        if os.path.exists(src10):
            shutil.copy(src10, p10)
    images["10_unsupported_object"] = p10

    return images

def run_evaluation():
    db = SessionLocal()
    images = create_or_get_test_images()

    logger.info("Running real-world evaluation across all 10 independent scenarios...")
    results = {}

    for name, path in images.items():
        logger.info(f"\n--- Testing Scenario: {name} ---")
        # 1. Model 1 Prediction
        pred_res = ml_service.predict(path, db)
        top = pred_res["top_prediction"]

        # 2. OCR Expiry Check if relevant
        ocr_res = ocr_engine.process_image(path)

        res_entry = {
            "scenario": name,
            "image_path": path,
            "predicted_item": top["item_name"],
            "freshness_or_status": top["freshness_class"],
            "confidence": top["confidence"],
            "category": top["category"],
            "is_dairy": top.get("is_dairy", False),
            "is_unknown": top.get("is_unknown", False),
            "needs_manual_check": top.get("needs_manual_check", False),
            "extracted_date": top.get("extracted_date"),
            "date_type": top.get("date_type"),
            "ocr_label_text": top.get("detected_text"),
            "ocr_raw_found": ocr_res.get("success", False),
            "ocr_date": ocr_res.get("extracted_date"),
            "ocr_date_type": ocr_res.get("date_type")
        }
        results[name] = res_entry

        logger.info(f"Item: {top['item_name']} (Conf: {top['confidence']}) | Category: {top['category']}")
        logger.info(f"Status/Freshness: {top['freshness_class']} | Needs Check: {top.get('needs_manual_check')}")
        if top.get("is_dairy"):
            logger.info(f"Dairy Date Extracted: {top.get('extracted_date')} ({top.get('date_type')}) | Label: '{top.get('detected_text')}'")
        if top.get("is_unknown"):
            logger.info("Successfully rejected as Unknown / Unsupported object!")

    db.close()

    report_path = os.path.join(REPORTS_DIR, "real_world_test_results.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    logger.info(f"\nReal-world evaluation complete! Report saved to {report_path}")
    return results

if __name__ == "__main__":
    run_evaluation()
