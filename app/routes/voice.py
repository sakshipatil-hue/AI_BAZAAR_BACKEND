"""Voice entry routes."""
from fastapi import APIRouter, Depends, File, Form, UploadFile
from app.middleware.auth import get_current_shopkeeper
from app.models import Shopkeeper

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.post("/")
async def voice_entry(
    audio: UploadFile = File(...),
    language: str = Form(default="en"),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    return {
        "transcript": "Voice feature requires OpenAI API key",
        "intent": "unknown",
        "reply_text": "Please add your OpenAI API key to enable voice features.",
        "reply_audio_url": None,
    }