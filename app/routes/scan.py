"""Bill scan / OCR routes using Groq Vision."""
import base64
import tempfile
import os

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from app.middleware.auth import get_current_shopkeeper
from app.models import Shopkeeper
from app.config import settings

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.post("/")
async def scan_bill(
    image: UploadFile = File(...),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured.")

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Read image and convert to base64
        image_bytes = await image.read()
        base64_image = base64.b64encode(image_bytes).decode('utf-8')

        # Detect image type
        content_type = image.content_type or "image/jpeg"

        # Send to Groq Vision
        response = client.chat.completions.create(
            model=settings.GROQ_VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{content_type};base64,{base64_image}"
                            }
                        },
                        {
                            "type": "text",
                            "text": """This is a shop register or bill photo from an Indian shopkeeper.
Extract all items, quantities and prices you can see.
Respond ONLY with a JSON object like this:
{
    "raw_text": "all text you can read from the image",
    "items": [
        {"name": "item name", "quantity": number, "unit": "kg/piece/litre", "price": number}
    ],
    "total": number or null,
    "date": "date if visible or null"
}
Return ONLY valid JSON, no other text."""
                        }
                    ]
                }
            ],
            max_tokens=1000,
        )

        # Parse response
        import json
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {
                "raw_text": raw,
                "items": [],
                "total": None,
                "date": None
            }

        return {
            "raw_text": parsed.get("raw_text", ""),
            "parsed_items": parsed.get("items", []),
            "total": parsed.get("total"),
            "date": parsed.get("date"),
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"OCR processing failed: {str(e)}"
        )