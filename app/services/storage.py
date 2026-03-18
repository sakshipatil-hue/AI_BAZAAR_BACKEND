"""
Supabase Storage Service
- Upload invoice PDFs to 'invoices' bucket
- Upload TTS audio to 'audio' bucket
- Returns public URLs
- Auto-creates buckets if they don't exist
"""
import os
import uuid

from app.config import settings
from app.supabase_client import supabase_admin


def ensure_buckets_exist():
    """Create storage buckets if they don't exist."""
    try:
        existing = supabase_admin.storage.list_buckets()
        existing_names = [b.name for b in existing]

        for bucket in [settings.SUPABASE_INVOICE_BUCKET, settings.SUPABASE_AUDIO_BUCKET]:
            if bucket not in existing_names:
                supabase_admin.storage.create_bucket(
                    bucket,
                    options={"public": False}
                )
                print(f"✅ Created Supabase bucket: {bucket}")
    except Exception as e:
        print(f"⚠️ Could not ensure buckets exist: {e}")


def upload_invoice_pdf(pdf_path: str, invoice_number: str) -> str:
    """
    Upload a PDF file to Supabase 'invoices' bucket.
    Returns the signed URL (valid 1 year).
    """
    try:
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        file_name = f"{invoice_number}.pdf"

        supabase_admin.storage.from_(settings.SUPABASE_INVOICE_BUCKET).upload(
            path=file_name,
            file=pdf_bytes,
            file_options={"content-type": "application/pdf", "upsert": "true"},
        )

        # Generate signed URL valid for 1 year
        signed = supabase_admin.storage.from_(
            settings.SUPABASE_INVOICE_BUCKET
        ).create_signed_url(file_name, expires_in=31536000)

        return signed.get("signedURL") or signed.get("signed_url", "")

    except Exception as e:
        print(f"⚠️ Supabase PDF upload failed: {e}")
        return ""


def upload_audio_file(audio_path: str) -> str:
    """
    Upload a TTS audio file to Supabase 'audio' bucket.
    Returns public URL.
    """
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()

        file_name = f"{uuid.uuid4().hex}.mp3"

        supabase_admin.storage.from_(settings.SUPABASE_AUDIO_BUCKET).upload(
            path=file_name,
            file=audio_bytes,
            file_options={"content-type": "audio/mpeg", "upsert": "true"},
        )

        signed = supabase_admin.storage.from_(
            settings.SUPABASE_AUDIO_BUCKET
        ).create_signed_url(file_name, expires_in=3600)  # 1 hour

        return signed.get("signedURL") or signed.get("signed_url", "")

    except Exception as e:
        print(f"⚠️ Supabase audio upload failed: {e}")
        return ""


def get_invoice_url(invoice_number: str) -> str:
    """Get a fresh signed URL for an existing invoice."""
    try:
        signed = supabase_admin.storage.from_(
            settings.SUPABASE_INVOICE_BUCKET
        ).create_signed_url(f"{invoice_number}.pdf", expires_in=3600)
        return signed.get("signedURL") or ""
    except Exception:
        return ""
