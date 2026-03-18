"""
Billing service
- Validates sale items, deducts stock, computes GST
- Generates PDF invoice with ReportLab
- Uploads PDF to Supabase Storage
- Returns Supabase signed URL
"""
import os
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Invoice, Product, Sale, SaleItem, Shopkeeper
from app.schemas import SaleCreate
from app.services.storage import upload_invoice_pdf


def process_sale(payload: SaleCreate, shopkeeper: Shopkeeper, db: Session) -> Sale:
    """Validate items, deduct inventory, persist sale."""
    sale = Sale(
        shopkeeper_id=shopkeeper.id,
        customer_name=payload.customer_name,
        customer_phone=payload.customer_phone,
        payment_mode=payload.payment_mode,
        notes=payload.notes,
    )
    db.add(sale)
    db.flush()

    subtotal = 0.0
    gst_total = 0.0

    for item_in in payload.items:
        product = db.query(Product).filter(
            Product.id == item_in.product_id,
            Product.shopkeeper_id == shopkeeper.id,
            Product.is_active == True,
        ).first()
        if not product:
            db.rollback()
            raise ValueError(f"Product id={item_in.product_id} not found")
        if product.quantity < item_in.quantity:
            db.rollback()
            raise ValueError(f"Insufficient stock for '{product.name}'")

        line_base = round(product.selling_price * item_in.quantity, 2)
        line_gst = round(line_base * product.gst_rate / 100, 2)
        line_total = round(line_base + line_gst, 2)

        db.add(SaleItem(
            sale_id=sale.id,
            product_id=product.id,
            product_name=product.name,
            quantity=item_in.quantity,
            unit_price=product.selling_price,
            gst_rate=product.gst_rate,
            line_total=line_total,
        ))

        product.quantity -= item_in.quantity
        subtotal += line_base
        gst_total += line_gst

    sale.subtotal = round(subtotal, 2)
    sale.gst_amount = round(gst_total, 2)
    sale.total = round(subtotal + gst_total, 2)

    db.commit()
    db.refresh(sale)
    return sale


def generate_and_upload_invoice(sale: Sale, shopkeeper: Shopkeeper) -> tuple[str, str]:
    """
    Generate PDF locally, upload to Supabase Storage.
    Returns (invoice_number, supabase_url)
    """
    invoice_number = f"INV-{shopkeeper.id:04d}-{sale.id:06d}"

    # Generate PDF locally first
    os.makedirs(settings.INVOICE_DIR, exist_ok=True)
    local_path = os.path.join(settings.INVOICE_DIR, f"{invoice_number}.pdf")
    _render_pdf(local_path, sale, shopkeeper, invoice_number)

    # Upload to Supabase Storage
    pdf_url = upload_invoice_pdf(local_path, invoice_number)

    return invoice_number, pdf_url, local_path


def _render_pdf(filepath: str, sale: Sale, shopkeeper: Shopkeeper, invoice_number: str):
    """Render the GST invoice PDF with ReportLab."""
    doc = SimpleDocTemplate(filepath, pagesize=A4,
                            rightMargin=2*cm, leftMargin=2*cm,
                            topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    elements = []

    elements.append(Paragraph(f"<b>{shopkeeper.shop_name or shopkeeper.name}</b>", styles["Title"]))
    if shopkeeper.gst_number:
        elements.append(Paragraph(f"GSTIN: {shopkeeper.gst_number}", styles["Normal"]))
    elements.append(Paragraph(f"Phone: {shopkeeper.phone}", styles["Normal"]))
    elements.append(Spacer(1, 0.3*cm))
    elements.append(Paragraph(f"<b>Tax Invoice</b> – {invoice_number}", styles["Heading2"]))
    elements.append(Paragraph(f"Date: {sale.created_at.strftime('%d %b %Y, %I:%M %p')}", styles["Normal"]))
    if sale.customer_name:
        elements.append(Paragraph(f"Customer: {sale.customer_name}  |  {sale.customer_phone or ''}", styles["Normal"]))
    elements.append(Spacer(1, 0.5*cm))

    table_data = [["#", "Item", "Qty", "Rate (₹)", "GST%", "Amount (₹)"]]
    for i, item in enumerate(sale.items, 1):
        table_data.append([str(i), item.product_name, str(item.quantity),
                           f"{item.unit_price:.2f}", f"{item.gst_rate}%", f"{item.line_total:.2f}"])

    table = Table(table_data, colWidths=[1*cm, 7*cm, 2*cm, 2.5*cm, 1.5*cm, 3*cm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a73e8")),
        ("TEXTCOLOR",  (0, 0), (-1, 0), colors.white),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("ALIGN",      (2, 0), (-1, -1), "RIGHT"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
        ("GRID",       (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ("FONTSIZE",   (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.4*cm))

    totals = [
        ["", "", "", "", "Subtotal:", f"₹{sale.subtotal:.2f}"],
        ["", "", "", "", "GST:",      f"₹{sale.gst_amount:.2f}"],
        ["", "", "", "", "TOTAL:",    f"₹{sale.total:.2f}"],
    ]
    totals_table = Table(totals, colWidths=[1*cm, 7*cm, 2*cm, 2.5*cm, 2*cm, 3*cm])
    totals_table.setStyle(TableStyle([
        ("ALIGN",    (4, 0), (-1, -1), "RIGHT"),
        ("FONTNAME", (4, 2), (-1, 2), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("LINEABOVE", (4, 2), (-1, 2), 1, colors.black),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Payment mode: {sale.payment_mode.upper()}", styles["Normal"]))
    elements.append(Spacer(1, 1*cm))
    elements.append(Paragraph("Thank you for your purchase!", styles["Normal"]))

    doc.build(elements)
