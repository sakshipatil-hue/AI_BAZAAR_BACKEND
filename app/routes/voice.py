"""Voice entry routes using Groq with real-time inventory updates."""
import os
import json
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.middleware.auth import get_current_shopkeeper
from app.models import Shopkeeper, Product, Sale, SaleItem
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.post("/")
async def voice_entry(
    audio: UploadFile = File(...),
    language: str = Form(default="hi"),
    current: Shopkeeper = Depends(get_current_shopkeeper),
    db: Session = Depends(get_db),
):
    if not settings.GROQ_API_KEY:
        raise HTTPException(status_code=503, detail="GROQ_API_KEY not configured.")

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        lang_map = {
            "hi": "hi", "hi-IN": "hi",
            "en": "en", "en-IN": "en",
            "ta": "ta", "ta-IN": "ta",
            "gu": "gu", "gu-IN": "gu",
            "te": "te", "te-IN": "te",
        }
        whisper_lang = lang_map.get(language, "hi")

        # Save audio to temp file
        audio_bytes = await audio.read()
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Step 1 — Transcribe with Whisper
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model=settings.GROQ_TRANSCRIPTION_MODEL,
                file=f,
                language=whisper_lang,
            )
        transcript = transcription.text
        os.unlink(tmp_path)

        # Step 2 — Extract structured data with Llama
        extract_prompt = f"""You are an AI assistant for Indian shopkeepers.
Extract sales/inventory information from this voice command: "{transcript}"

Respond ONLY with a JSON object like this:
{{
    "intent": "sale" or "stock_add" or "query" or "unknown",
    "items": [
        {{"name": "item name", "quantity": number, "unit": "kg/piece/litre etc"}}
    ],
    "customer_name": "customer name or null",
    "reply": "friendly response in same language as input"
}}

Examples:
- "aaj 5 kilo atta bika" → intent: sale, items: [{{"name": "atta", "quantity": 5, "unit": "kg"}}]
- "10 kg chawal aaya" → intent: stock_add, items: [{{"name": "chawal", "quantity": 10, "unit": "kg"}}]
- "sugar ka stock kitna hai" → intent: query, items: []

Return ONLY valid JSON, no other text."""

        chat = client.chat.completions.create(
            model=settings.GROQ_CHAT_MODEL,
            messages=[
                {"role": "user", "content": extract_prompt}
            ],
            max_tokens=300,
        )

        # Parse JSON response
        raw = chat.choices[0].message.content.strip()
        # Clean up response
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        intent = parsed.get("intent", "unknown")
        items = parsed.get("items", [])
        customer_name = parsed.get("customer_name")
        reply_text = parsed.get("reply", "Understood!")

        action_result = None

        # Step 3 — Execute action based on intent
        if intent == "sale" and items:
            action_result = await process_voice_sale(
                items, customer_name, current, db
            )

        elif intent == "stock_add" and items:
            action_result = await process_voice_stock_add(
                items, current, db
            )

        elif intent == "query":
            # Get current stock info
            products = db.query(Product).filter(
                Product.shopkeeper_id == current.id,
                Product.is_active == True
            ).all()
            stock_info = ", ".join([f"{p.name}: {p.quantity} {p.unit}" for p in products[:5]])
            reply_text = f"Current stock: {stock_info}" if stock_info else reply_text

        return {
            "transcript": transcript,
            "intent": intent,
            "reply_text": reply_text,
            "action_result": action_result,
            "items": items,
        }

    except json.JSONDecodeError:
        # If JSON parsing fails, just return transcript
        return {
            "transcript": transcript,
            "intent": "unknown",
            "reply_text": "I understood but couldn't process. Please try again.",
            "action_result": None,
            "items": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


async def process_voice_sale(items, customer_name, shopkeeper, db):
    """Record a sale from voice command."""
    results = []
    total = 0

    for item in items:
        # Find product by name (fuzzy match)
        product = db.query(Product).filter(
            Product.shopkeeper_id == shopkeeper.id,
            Product.is_active == True,
            Product.name.ilike(f"%{item['name']}%")
        ).first()

        if product and product.quantity >= item['quantity']:
            # Deduct stock
            product.quantity -= item['quantity']
            line_total = product.selling_price * item['quantity']
            total += line_total
            results.append({
                "name": product.name,
                "quantity": item['quantity'],
                "unit": item.get('unit', product.unit),
                "total": line_total,
                "status": "sold"
            })
        else:
            results.append({
                "name": item['name'],
                "quantity": item['quantity'],
                "status": "not_found" if not product else "insufficient_stock"
            })

    # Save sale if any items processed
    if any(r['status'] == 'sold' for r in results):
        sale = Sale(
            shopkeeper_id=shopkeeper.id,
            customer_name=customer_name,
            subtotal=total,
            gst_amount=round(total * 0.05, 2),
            total=round(total * 1.05, 2),
            payment_mode="cash",
            notes="Via voice entry"
        )
        db.add(sale)
        db.commit()

    return {"type": "sale", "items": results, "total": total}


async def process_voice_stock_add(items, shopkeeper, db):
    """Add stock from voice command."""
    results = []

    for item in items:
        product = db.query(Product).filter(
            Product.shopkeeper_id == shopkeeper.id,
            Product.is_active == True,
            Product.name.ilike(f"%{item['name']}%")
        ).first()

        if product:
            product.quantity += item['quantity']
            db.commit()
            results.append({
                "name": product.name,
                "added": item['quantity'],
                "new_stock": product.quantity,
                "status": "updated"
            })
        else:
            results.append({
                "name": item['name'],
                "status": "not_found"
            })

    return {"type": "stock_add", "items": results}