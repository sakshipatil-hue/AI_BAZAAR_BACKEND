"""Pydantic v2 schemas – request bodies and response shapes."""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


# ────────────────────────────────────────────────────────────────
#  AUTH
# ────────────────────────────────────────────────────────────────
class ShopkeeperCreate(BaseModel):
    name: str
    phone: str
    password: str
    email: Optional[EmailStr] = None
    whatsapp_number: Optional[str] = None
    shop_name: Optional[str] = None
    gst_number: Optional[str] = None
    language: str = "en"


class ShopkeeperOut(BaseModel):
    id: int
    name: str
    phone: str
    email: Optional[str] = None
    shop_name: Optional[str] = None
    gst_number: Optional[str] = None
    language: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    phone: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ────────────────────────────────────────────────────────────────
#  PRODUCT / INVENTORY
# ────────────────────────────────────────────────────────────────
class ProductCreate(BaseModel):
    name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    quantity: float = 0
    unit: str = "piece"
    purchase_price: float = 0
    selling_price: float = 0
    gst_rate: float = 5
    reorder_level: float = 10


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    reorder_level: Optional[float] = None
    gst_rate: Optional[float] = None


class ProductOut(BaseModel):
    id: int
    name: str
    sku: Optional[str] = None
    category: Optional[str] = None
    quantity: float
    unit: str
    purchase_price: float
    selling_price: float
    gst_rate: float
    reorder_level: float
    is_active: bool

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────────────────────
#  SALES & BILLING
# ────────────────────────────────────────────────────────────────
class SaleItemIn(BaseModel):
    product_id: int
    quantity: float

    @field_validator("quantity")
    @classmethod
    def positive_qty(cls, v):
        if v <= 0:
            raise ValueError("Quantity must be > 0")
        return v


class SaleCreate(BaseModel):
    items: list[SaleItemIn]
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_mode: str = "cash"
    notes: Optional[str] = None


class SaleItemOut(BaseModel):
    product_name: str
    quantity: float
    unit_price: float
    gst_rate: float
    line_total: float

    model_config = {"from_attributes": True}


class SaleOut(BaseModel):
    id: int
    customer_name: Optional[str] = None
    customer_phone: Optional[str] = None
    subtotal: float
    gst_amount: float
    total: float
    payment_mode: str
    created_at: datetime
    items: list[SaleItemOut]

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────────────────────
#  INVOICE
# ────────────────────────────────────────────────────────────────
class InvoiceOut(BaseModel):
    id: int
    invoice_number: str
    pdf_path: Optional[str] = None
    pdf_url: Optional[str] = None
    sent_via_whatsapp: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ────────────────────────────────────────────────────────────────
#  VOICE
# ────────────────────────────────────────────────────────────────
class VoiceResponse(BaseModel):
    transcript: str
    intent: str
    reply_text: str
    reply_audio_url: Optional[str] = None


# ────────────────────────────────────────────────────────────────
#  AI INSIGHTS
# ────────────────────────────────────────────────────────────────
class InsightResponse(BaseModel):
    summary: str
    top_sellers: list[dict]
    low_stock_items: list[dict]
    demand_predictions: list[dict]
    pricing_suggestions: list[dict]


# ────────────────────────────────────────────────────────────────
#  OCR SCAN
# ────────────────────────────────────────────────────────────────
class OCRResult(BaseModel):
    raw_text: str
    parsed_items: list[dict]