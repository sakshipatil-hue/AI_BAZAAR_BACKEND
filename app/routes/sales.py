"""Sales routes — create sale, list history, download invoice via Supabase URL."""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_shopkeeper
from app.models import Invoice, Sale, Shopkeeper
from app.schemas import InvoiceOut, SaleCreate, SaleOut
from app.services.billing import generate_and_upload_invoice, process_sale
from app.services.storage import get_invoice_url
from app.services.whatsapp import send_invoice_whatsapp

router = APIRouter(prefix="/api/sales", tags=["Sales & Billing"])


@router.post("/", response_model=SaleOut, status_code=201)
def create_sale(
    payload: SaleCreate,
    send_whatsapp: bool = False,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    try:
        sale = process_sale(payload, current, db)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # Generate PDF and upload to Supabase Storage
    invoice_number, pdf_url, local_path = generate_and_upload_invoice(sale, current)

    invoice = Invoice(
        sale_id=sale.id,
        invoice_number=invoice_number,
        pdf_url=pdf_url,
        pdf_path=local_path,
    )
    db.add(invoice)
    db.commit()
    db.refresh(sale)

    # Optionally send WhatsApp
    if send_whatsapp and payload.customer_phone:
        try:
            send_invoice_whatsapp(payload.customer_phone, invoice_number, local_path)
            invoice.sent_via_whatsapp = True
            db.commit()
        except Exception:
            pass

    return sale


@router.get("/", response_model=List[SaleOut])
def list_sales(
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    return (
        db.query(Sale)
        .filter(Sale.shopkeeper_id == current.id)
        .order_by(Sale.created_at.desc())
        .offset(skip).limit(limit).all()
    )


@router.get("/{sale_id}", response_model=SaleOut)
def get_sale(
    sale_id: int,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.shopkeeper_id == current.id).first()
    if not sale:
        raise HTTPException(status_code=404, detail="Sale not found")
    return sale


@router.get("/{sale_id}/invoice/download")
def download_invoice(
    sale_id: int,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    """Redirect to Supabase signed URL for the invoice PDF."""
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.shopkeeper_id == current.id).first()
    if not sale or not sale.invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Get fresh signed URL from Supabase
    url = get_invoice_url(sale.invoice.invoice_number)
    if not url:
        # Fallback to stored URL
        url = sale.invoice.pdf_url

    if not url:
        raise HTTPException(status_code=404, detail="Invoice file not found in storage")

    return RedirectResponse(url=url)


@router.post("/{sale_id}/invoice/whatsapp")
def send_whatsapp_invoice(
    sale_id: int,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.shopkeeper_id == current.id).first()
    if not sale or not sale.invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not sale.customer_phone:
        raise HTTPException(status_code=422, detail="No customer phone on this sale")

    try:
        send_invoice_whatsapp(sale.customer_phone, sale.invoice.invoice_number, sale.invoice.pdf_path or "")
        sale.invoice.sent_via_whatsapp = True
        db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"WhatsApp send failed: {e}")

    return {"status": "sent", "invoice": sale.invoice.invoice_number}
