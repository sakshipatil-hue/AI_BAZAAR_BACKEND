"""Voice entry routes using Groq with real-time inventory updates."""
import os
import json
import tempfile
from datetime import datetime

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
- "aaj ki bikri kitni hai" → intent: query, items: []
- "monthly revenue kya hai" → intent: query, items: []

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
            reply_text = await process_voice_query(
                transcript, current, db, client
            )

        return {
            "transcript": transcript,
            "intent": intent,
            "reply_text": reply_text,
            "action_result": action_result,
            "items": items,
        }

    except json.JSONDecodeError:
        return {
            "transcript": transcript,
            "intent": "unknown",
            "reply_text": "I understood but couldn't process. Please try again.",
            "action_result": None,
            "items": [],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Voice processing failed: {str(e)}")


async def process_voice_query(transcript, shopkeeper, db, client):
    """Answer business queries using real data."""

    # Get products
    products = db.query(Product).filter(
        Product.shopkeeper_id == shopkeeper.id,
        Product.is_active == True
    ).all()

    # Get all sales
    all_sales = db.query(Sale).filter(
        Sale.shopkeeper_id == shopkeeper.id
    ).all()

    # Calculate metrics
    today = datetime.utcnow().date()
    first_of_month = today.replace(day=1)

    today_sales = [s for s in all_sales if s.created_at.date() == today]
    month_sales = [s for s in all_sales if s.created_at.date() >= first_of_month]

    today_revenue = sum(s.total for s in today_sales)
    month_revenue = sum(s.total for s in month_sales)
    total_revenue = sum(s.total for s in all_sales)

    # Estimated profit (20% margin)
    today_profit = today_revenue * 0.20
    month_profit = month_revenue * 0.20
    total_profit = total_revenue * 0.20

    # Stock value
    stock_value = sum(p.quantity * p.purchase_price for p in products)

    # Low stock items
    low_stock = [p for p in products if p.quantity <= p.reorder_level]

    # Build business context
    business_context = f"""
You are an AI assistant for an Indian shopkeeper. Answer their question using this real business data:

SALES DATA:
- Today's sales: {len(today_sales)} transactions, Revenue: ₹{today_revenue:.2f}, Estimated Profit: ₹{today_profit:.2f}
- This month's sales: {len(month_sales)} transactions, Revenue: ₹{month_revenue:.2f}, Estimated Profit: ₹{month_profit:.2f}
- Total all-time sales: {len(all_sales)} transactions, Revenue: ₹{total_revenue:.2f}, Total Profit: ₹{total_profit:.2f}

INVENTORY DATA:
- Total products: {len(products)}
- Stock value: ₹{stock_value:.2f}
- Low stock items ({len(low_stock)}): {', '.join([f"{p.name} ({p.quantity} {p.unit})" for p in low_stock[:5]]) if low_stock else 'None'}
- Top products: {', '.join([f"{p.name}: {p.quantity} {p.unit}" for p in products[:5]])}

User question: "{transcript}"

Answer the question clearly and specifically using the data above.
Respond in the same language as the question (Hindi/English/Tamil etc).
Keep response under 3 sentences. Be friendly and helpful.
If profit data is estimated, mention it's an estimate based on 20% margin."""

    query_chat = client.chat.completions.create(
        model=settings.GROQ_CHAT_MODEL,
        messages=[
            {"role": "user", "content": business_context}
        ],
        max_tokens=200,
    )
    return query_chat.choices[0].message.content


async def process_voice_sale(items, customer_name, shopkeeper, db):
    """Record a sale from voice command."""
    results = []
    total = 0

    for item in items:
        product = db.query(Product).filter(
            Product.shopkeeper_id == shopkeeper.id,
            Product.is_active == True,
            Product.name.ilike(f"%{item['name']}%")
        ).first()

        if product and product.quantity >= item['quantity']:
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
                "unit": product.unit,
                "status": "updated"
            })
        else:
            results.append({
                "name": item['name'],
                "status": "not_found"
            })

    return {"type": "stock_add", "items": results}