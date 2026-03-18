"""Bill scan / OCR routes."""
from fastapi import APIRouter, Depends, File, UploadFile
from app.middleware.auth import get_current_shopkeeper
from app.models import Shopkeeper

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.post("/")
async def scan_bill(
    image: UploadFile = File(...),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    return {
        "raw_text": "OCR feature requires OpenAI API key",
        "parsed_items": [],
    }