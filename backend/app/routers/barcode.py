from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import BarcodeProductOut
from app.services.barcode_service import lookup_barcode
from app.models import User
from app.security import get_current_user

router = APIRouter(prefix="/barcode", tags=["Barcode Scanning"])

@router.get("/{code}", response_model=BarcodeProductOut)
async def get_barcode_product(
    code: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if not code or len(code.strip()) < 3:
        raise HTTPException(status_code=400, detail="Invalid barcode format")

    result = await lookup_barcode(code, db)
    return result
