import os
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import FoodImage, User
from app.schemas import FeedbackCreate, DatasetStatsOut
from app.services.ml_inference import SUPPORTED_ITEMS, FRESHNESS_CLASSES
from app.security import get_current_user

router = APIRouter(prefix="/dataset", tags=["Dataset & Retraining Loop"])

@router.post("/feedback")
def submit_label_feedback(
    feedback: FeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submits user correction for a predicted image, queuing it into pending review for retraining.
    """
    if feedback.food_image_id:
        img = db.query(FoodImage).filter(FoodImage.id == feedback.food_image_id).first()
        if img:
            img.verified_label = feedback.correct_item_name
            img.verified_freshness = feedback.correct_freshness
            img.split = "pending"
            db.commit()
            return {"message": "Feedback submitted. Image added to pending retraining pool.", "image_id": img.id}

    new_img = FoodImage(
        path=feedback.image_path or "/storage/uploads/demo.jpg",
        verified_label=feedback.correct_item_name,
        verified_freshness=feedback.correct_freshness,
        confidence=1.0,
        split="pending"
    )
    db.add(new_img)
    db.commit()
    db.refresh(new_img)
    return {"message": "Feedback created for retraining", "image_id": new_img.id}

@router.get("/stats")
def get_dataset_stats(db: Session = Depends(get_db)):
    all_imgs = db.query(FoodImage).all()
    
    splits = {"train": 0, "val": 0, "test": 0, "pending": 0}
    classes = {c: 0 for c in FRESHNESS_CLASSES}
    items_count = {it.capitalize(): 0 for it in SUPPORTED_ITEMS}

    for img in all_imgs:
        splits[img.split] = splits.get(img.split, 0) + 1
        label = img.verified_label or img.predicted_label
        fresh = img.verified_freshness or img.predicted_freshness
        if fresh in classes:
            classes[fresh] += 1
        if label and label.capitalize() in items_count:
            items_count[label.capitalize()] += 1

    return {
        "total_images": len(all_imgs),
        "splits": splits,
        "classes": classes,
        "items": items_count,
        "pending_count": splits.get("pending", 0),
        "supported_items": [s.capitalize() for s in SUPPORTED_ITEMS],
        "freshness_classes": FRESHNESS_CLASSES
    }

@router.get("/pending")
def get_pending_images(db: Session = Depends(get_db)):
    pending = db.query(FoodImage).filter(FoodImage.split == "pending").order_by(FoodImage.created_at.desc()).all()
    return [
        {
            "id": img.id,
            "path": img.path,
            "predicted_label": img.predicted_label,
            "predicted_freshness": img.predicted_freshness,
            "confidence": img.confidence,
            "verified_label": img.verified_label or img.predicted_label,
            "verified_freshness": img.verified_freshness or img.predicted_freshness,
            "created_at": img.created_at
        }
        for img in pending
    ]

@router.post("/verify/{image_id}")
def verify_image(
    image_id: int,
    action: str,  # approve or reject
    target_split: str = "train",
    db: Session = Depends(get_db)
):
    img = db.query(FoodImage).filter(FoodImage.id == image_id).first()
    if not img:
        raise HTTPException(status_code=404, detail="Image not found")

    if action == "approve":
        img.split = target_split
        db.commit()
        return {"message": f"Image {image_id} approved and moved to {target_split} dataset"}
    else:
        db.delete(img)
        db.commit()
        return {"message": f"Image {image_id} rejected and discarded"}
