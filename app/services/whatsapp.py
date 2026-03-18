"""WhatsApp service using Twilio."""
import os
from app.config import settings


def send_invoice_whatsapp(phone: str, invoice_number: str, pdf_path: str) -> bool:
    """Send invoice via WhatsApp using Twilio."""
    try:
        from twilio.rest import Client
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        client.messages.create(
            from_=settings.TWILIO_WHATSAPP_FROM,
            to=f"whatsapp:+91{phone}",
            body=f"Your invoice {invoice_number} is ready. Thank you for shopping with us!"
        )
        return True
    except Exception as e:
        print(f"WhatsApp send failed: {e}")
        return False