"""Voice entry routes using Groq (free alternative to OpenAI)."""
import os
import tempfile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.middleware.auth import get_current_shopkeeper
from app.models import Shopkeeper
from app.config import settings

router = APIRouter(prefix="/api/voice", tags=["Voice"])


@router.post("/")
async def voice_entry(
    audio: UploadFile = File(...),
    language: str = Form(default="hi"),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    if not settings.GROQ_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="Voice feature not configured. Please add GROQ_API_KEY."
        )

    try:
        from groq import Groq
        client = Groq(api_key=settings.GROQ_API_KEY)

        # Map language codes
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
        with tempfile.NamedTemporaryFile(
            suffix=".webm", delete=False
        ) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        # Step 1 — Transcribe with Whisper via Groq
        with open(tmp_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-large-v3",
                file=f,
                language=whisper_lang,
            )
        transcript = transcription.text
        os.unlink(tmp_path)

        # Step 2 — Understand intent with Llama 3
        system_prompt = """You are an AI assistant for Indian shopkeepers.
The shopkeeper will say something about their shop in Hindi, Tamil, Gujarati, Telugu or English.
Understand what they said and respond helpfully in the same language.
Keep responses short (1-2 sentences). Be friendly and helpful.
Examples:
- "aaj 5 kilo atta bika" → Record that 5 kg flour was sold today
- "sugar ka stock kam hai" → Note that sugar stock is low
- "Ramesh ko 2 kg chawal diya" → Record 2 kg rice given to Ramesh"""

        chat = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": transcript}
            ],
            max_tokens=150,
        )
        reply_text = chat.choices[0].message.content

        # Detect intent
        transcript_lower = transcript.lower()
        intent = "unknown"
        sale_keywords = ["bika", "becha", "sold", "sale", "diya", "liya"]
        stock_keywords = ["stock", "kam", "khatam", "low", "finish", "order"]
        if any(w in transcript_lower for w in sale_keywords):
            intent = "sale"
        elif any(w in transcript_lower for w in stock_keywords):
            intent = "stock_alert"

        return {
            "transcript": transcript,
            "intent": intent,
            "reply_text": reply_text,
            "reply_audio_url": None,
        }

    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="Groq package not installed. Run: pip install groq"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Voice processing failed: {str(e)}"
        )