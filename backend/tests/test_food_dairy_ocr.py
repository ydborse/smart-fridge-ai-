"""
Unit and regression tests for:
1. Model 1: Food and Packaged Dairy Classifier (11 classes)
2. Model 2: OCR Date Extraction, Semantic Parsing, and Date Status Calculation
"""

import os
import pytest
from datetime import datetime, timedelta, timezone
import numpy as np
import cv2
from PIL import Image, ImageDraw

from app.services.ml_inference import ml_service
from app.services.ocr_service import ocr_engine, extract_expiry_date
from app.database import SessionLocal

@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def test_food_classifier_classes():
    """Verify all required produce and dairy classes plus unknown are loaded."""
    expected_classes = [
        "apple", "banana", "broccoli", "capsicum", "carrot", "onion", "orange",
        "packaged_milk", "packaged_paneer", "packaged_yogurt", "potato",
        "strawberry", "tomato", "unknown"
    ]
    assert ml_service.food_model is not None, "Food classifier model failed to load"
    assert len(ml_service.food_classes) >= 11
    for cls in expected_classes:
        assert cls in ml_service.food_classes, f"Missing required class: {cls}"

def test_ocr_expiry_date_formats(tmp_path):
    """Test OCR date parsing with various common packaging date formats and prefixes."""
    test_cases = [
        ("EXP: 25/11/2026", "2026-11-25", "EXPIRY"),
        ("USE BY: 18-05-2026", "2026-05-18", "EXPIRY"),
        ("BEST BEFORE: 12.08.2026", "2026-08-12", "BEST_BEFORE"),
        ("PKD: 10/04/2026", "2026-04-15", "ESTIMATED_FROM_MFG"),  # Milk shelf life = 5d -> 10 + 5 = 15
        ("EXP: 06 JUN 2026", "2026-06-06", "EXPIRY"),
        ("BB: 30-12-26", "2026-12-30", "BEST_BEFORE")
    ]

    for text, expected_date_str, expected_type in test_cases:
        img = Image.new("RGB", (550, 120), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        draw.text((30, 45), text, fill=(0, 0, 0))
        
        test_file = str(tmp_path / f"test_{expected_type}_{expected_date_str}.jpg")
        img.save(test_file)

        res = ocr_engine.process_image(test_file, product_item="packaged_milk")
        assert res["success"] is True, f"Failed to detect text: {text}"
        assert res["extracted_date"] == expected_date_str, f"Date mismatch for '{text}': got {res['extracted_date']}"
        assert res["date_type"] == expected_type, f"Type mismatch for '{text}': got {res['date_type']}"

def test_ocr_manufacturing_date_not_treated_as_expiry(tmp_path):
    """
    CRITICAL REQUIREMENT: Do not treat the manufacturing date as the expiry date.
    When only PKD/MFG is found, calculate estimated date using known shelf life.
    """
    mfg_text = "PKD: 01/05/2026"
    img = Image.new("RGB", (500, 120), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    draw.text((30, 45), mfg_text, fill=(0, 0, 0))
    
    test_file = str(tmp_path / "test_mfg.jpg")
    img.save(test_file)

    # For paneer (shelf life = 7 days)
    res = ocr_engine.process_image(test_file, product_item="packaged_paneer")
    assert res["success"] is True
    assert res["date_type"] == "ESTIMATED_FROM_MFG"
    assert res["is_estimated"] is True
    # MFG was 2026-05-01, Paneer shelf life is 7 days -> 2026-05-08
    assert res["extracted_date"] == "2026-05-08"

def test_ocr_date_status_expired_and_fresh(tmp_path):
    """Verify expired vs fresh status comparison against current date."""
    today = datetime.now(timezone.utc).date()
    past_date = today - timedelta(days=20)
    future_date = today + timedelta(days=20)

    # Past date
    img_past = Image.new("RGB", (500, 120), (255, 255, 255))
    draw_past = ImageDraw.Draw(img_past)
    draw_past.text((30, 45), f"EXP: {past_date.strftime('%d/%m/%Y')}", fill=(0, 0, 0))
    file_past = str(tmp_path / "past.jpg")
    img_past.save(file_past)
    res_past = ocr_engine.process_image(file_past)
    assert res_past["date_status"] == "Expired"

    # Future date
    img_future = Image.new("RGB", (500, 120), (255, 255, 255))
    draw_future = ImageDraw.Draw(img_future)
    draw_future.text((30, 45), f"EXP: {future_date.strftime('%d/%m/%Y')}", fill=(0, 0, 0))
    file_future = str(tmp_path / "future.jpg")
    img_future.save(file_future)
    res_future = ocr_engine.process_image(file_future)
    assert res_future["date_status"] == "Fresh"

def test_ocr_no_fake_fallback_on_blank_image(tmp_path):
    """
    CRITICAL REQUIREMENT: Do not return fake predictions or hardcoded expiry dates.
    When an image has no readable date, return success=False and parsed_date=None.
    """
    blank_img = np.ones((200, 200, 3), dtype=np.uint8) * 240
    blank_file = str(tmp_path / "blank.jpg")
    cv2.imwrite(blank_file, blank_img)

    res = ocr_engine.process_image(blank_file)
    assert res["success"] is False
    assert res["extracted_date"] is None
    assert res["needs_manual_check"] is True

    parsed_dt, label, conf = extract_expiry_date(blank_file)
    assert parsed_dt is None
    assert conf == 0.0

def test_dairy_decoupled_from_visual_produce_freshness(db, tmp_path):
    """
    CRITICAL REQUIREMENT: For packaged dairy products, show the extracted package date
    and date-based status separately from any visual freshness prediction.
    Do not classify dairy products as Fresh or Rotten visual produce stages.
    """
    # Create a dummy image
    img = np.ones((224, 224, 3), dtype=np.uint8) * 200
    test_file = str(tmp_path / "dummy_milk.jpg")
    cv2.imwrite(test_file, img)

    # Call format prediction for packaged_milk
    pred = ml_service._format_prediction(
        item_name="packaged_milk",
        freshness="Fresh",
        confidence=0.88,
        db=db,
        is_dairy=True,
        is_unknown=False,
        ocr_data={"success": True, "date_status": "Fresh", "extracted_date": "2026-11-20", "date_type": "EXPIRY", "confidence": 0.92}
    )

    assert pred["is_dairy"] is True
    assert pred["category"] == "Dairy"
    assert pred["item_type"] == "packaged"
    assert pred["date_type"] == "EXPIRY"
    assert pred["extracted_date"] == "2026-11-20"

def test_unknown_rejection(db):
    """Verify that unsupported objects / non-food inputs return Unknown."""
    pred = ml_service._format_prediction(
        item_name="unknown",
        freshness="Uncertain",
        confidence=0.91,
        db=db,
        is_dairy=False,
        is_unknown=True
    )
    assert pred["is_unknown"] is True
    assert pred["item_name"] == "Unknown / Unsupported"
    assert pred["category"] == "Other"
    assert pred["needs_manual_check"] is True
