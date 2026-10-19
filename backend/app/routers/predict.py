import os
import uuid
import shutil
import logging
from typing import Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.config import settings
from app.models import FoodImage, FoodItem, User
from app.schemas import PredictionResponse, DairyPredictionResponse
from app.services.ml_inference import ml_service
from app.services.dairy_classifier import dairy_service
from app.security import get_current_user
from app.services.yolo_detection import yolo_detection_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/predict", tags=["AI Recognition"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

@router.post("/objects")
async def detect_food_objects(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ext = os.path.splitext(file.filename or "")[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported image type. Use JPG, JPEG, PNG, or WEBP.",
        )

    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(
        settings.UPLOAD_DIR,
        f"yolo_{uuid.uuid4().hex}{ext}",
    )

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return yolo_detection_service.predict(file_path, db)

    except Exception:
        logger.exception("YOLO object detection failed")
        raise HTTPException(
            status_code=500,
            detail="YOLO detection failed. Check the backend logs.",
        )

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@router.post("", response_model=PredictionResponse)
async def predict_freshness(
    file: UploadFile = File(...),
    food_item_id: Optional[int] = Query(None, description="Optional tracked food item ID to associate and update"),
    use_webcam_model: bool = Query(False, description="Use the 10-class produce model for webcam recognition"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Run ML inference
        pred_res = ml_service.predict(
            file_path, db, use_webcam_model=use_webcam_model
        )

        top_pred = pred_res["top_prediction"]
        pred_freshness = top_pred.get("freshness_class", "Uncertain")
        confidence = top_pred.get("confidence", 0.0)

        # Record in FoodImage for dataset tracking and retraining loop
        food_img = FoodImage(
            food_item_id=food_item_id,
            path=f"/storage/uploads/{unique_filename}",
            predicted_label=top_pred["item_name"],
            predicted_freshness=pred_freshness,
            confidence=confidence,
            split="pending"
        )
        db.add(food_img)
        db.commit()
        db.refresh(food_img)

        # If a tracked food item was provided, update it and trigger spoilage alert if spoiled or rotten
        if food_item_id:
            food_item = db.query(FoodItem).filter(
                FoodItem.id == food_item_id,
                FoodItem.user_id == current_user.id
            ).first()
            if food_item:
                food_item.freshness_status = pred_freshness
                if not food_item.image_path:
                    food_item.image_path = food_img.path
                db.commit()

                if pred_freshness in ["Rotten", "Expired"]:
                    from app.services.alert_engine import create_spoilage_alert
                    try:
                        await create_spoilage_alert(
                            db=db,
                            user=current_user,
                            food=food_item,
                            confidence=confidence
                        )
                    except Exception as ex:
                        logger.warning(f"Failed to auto-trigger spoilage alert for item #{food_item_id}: {ex}")

        return pred_res
    except Exception as e:
        # If error occurs, remove the uploaded file
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Image prediction failed: {str(e)}")

@router.post("/dairy", response_model=DairyPredictionResponse)
async def predict_dairy_packaging(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dedicated endpoint for real dairy packaging recognition (Milk, Yogurt, Paneer, Cheese).
    Returns predicted packaging class, confidence, human-readable name, and storage advice.
    Note: Product category recognition is separate from freshness grading.
    """
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type. Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Generate unique filename
    unique_filename = f"dairy_{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # Run MobileNetV2 Dairy packaging inference
        dairy_res = dairy_service.predict(file_path)

        # Track image upload in FoodImage
        food_img = FoodImage(
            path=dairy_res["image_url"],
            predicted_label=dairy_res["display_name"],
            predicted_freshness="Packaged",
            confidence=dairy_res["confidence"],
            split="dairy_pending"
        )
        db.add(food_img)
        db.commit()

        return dairy_res
    except ValueError as ve:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Invalid image file: {str(ve)}")
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=500, detail=f"Dairy image prediction failed: {str(e)}")
