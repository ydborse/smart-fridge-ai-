import os
import uuid
import shutil
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from app.config import settings
from app.services.ocr_service import ocr_engine
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/ocr", tags=["OCR Expiry Detection"])

@router.post("/expiry")
async def read_expiry_from_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    unique_filename = f"ocr_{uuid.uuid4().hex}_{file.filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, unique_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        res = ocr_engine.process_image(file_path)
        return {
            "expiry_date": res.get("original_parsed_date"),
            "detected_text": res.get("detected_text"),
            "confidence": res.get("confidence", 0.0),
            "success": res.get("success", False),
            "date_type": res.get("date_type", "UNKNOWN"),
            "date_status": res.get("date_status", "Uncertain"),
            "extracted_date": res.get("extracted_date"),
            "is_estimated": res.get("is_estimated", False),
            "needs_manual_check": res.get("needs_manual_check", True),
            "raw_lines": res.get("raw_lines", [])
        }
    finally:
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
