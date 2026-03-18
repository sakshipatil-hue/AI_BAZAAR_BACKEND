"""ORM Models for AI Bazaar — Supabase PostgreSQL version."""
from datetime import datetime

from sqlalchemy import (
    Boolean, Column, DateTime, Float,
    ForeignKey, Integer, String, Text
)
from sqlalchemy.orm import relationship

from app.database import Base


class Shopkeeper(Base):
    __tablename__ = "shopkeepers"

    id = Column(Integer, primary_key=True, index=True)
    supabase_uid = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(120), nullable=False)
    phone = Column(String(20), unique=True, nullable=False)
    whatsapp_number = Column(String(20), nullable=True)
    email = Column(String(120), unique=True, nullable=True)
    shop_name = Column(String(200), nullable=True)
    gst_number = Column(String(20), nullable=True)
    language = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="shopkeeper", cascade="all, delete")
    sales = relationship("Sale", back_populates="shopkeeper", cascade="all, delete")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id"), nullable=False)
    name = Column(String(200), nullable=False)
    sku = Column(String(60), nullable=True)
    category = Column(String(80), nullable=True)
    quantity = Column(Float, default=0)
    unit = Column(String(20), default="piece")
    purchase_price = Column(Float, default=0)
    selling_price = Column(Float, default=0)
    gst_rate = Column(Float, default=5)
    reorder_level = Column(Float, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    shopkeeper = relationship("Shopkeeper", back_populates="products")
    sale_items = relationship("SaleItem", back_populates="product")


class Sale(Base):
    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    shopkeeper_id = Column(Integer, ForeignKey("shopkeepers.id"), nullable=False)
    customer_name = Column(String(120), nullable=True)
    customer_phone = Column(String(20), nullable=True)
    subtotal = Column(Float, default=0)
    gst_amount = Column(Float, default=0)
    total = Column(Float, default=0)
    payment_mode = Column(String(30), default="cash")
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    shopkeeper = relationship("Shopkeeper", back_populates="sales")
    items = relationship("SaleItem", back_populates="sale", cascade="all, delete")
    invoice = relationship("Invoice", back_populates="sale", uselist=False, cascade="all, delete")


class SaleItem(Base):
    __tablename__ = "sale_items"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    product_name = Column(String(200))
    quantity = Column(Float, nullable=False)
    unit_price = Column(Float, nullable=False)
    gst_rate = Column(Float, default=0)
    line_total = Column(Float, nullable=False)

    sale = relationship("Sale", back_populates="items")
    product = relationship("Product", back_populates="sale_items")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    sale_id = Column(Integer, ForeignKey("sales.id"), unique=True, nullable=False)
    invoice_number = Column(String(40), unique=True, nullable=False)
    # Supabase Storage public URL
    pdf_url = Column(String(1000), nullable=True)
    # Local fallback path
    pdf_path = Column(String(500), nullable=True)
    sent_via_whatsapp = Column(Boolean, default=False)
    sent_via_email = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    sale = relationship("Sale", back_populates="invoice")
