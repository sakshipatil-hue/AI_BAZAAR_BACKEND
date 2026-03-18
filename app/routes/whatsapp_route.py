"""WhatsApp webhook routes."""
from fastapi import APIRouter, Request

router = APIRouter(prefix="/api/whatsapp", tags=["WhatsApp"])


@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    return {"status": "ok"}