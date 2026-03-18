"""Inventory routes."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_shopkeeper
from app.models import Product, Shopkeeper
from app.schemas import ProductCreate, ProductOut, ProductUpdate

router = APIRouter(prefix="/api/inventory", tags=["Inventory"])


@router.get("/", response_model=List[ProductOut])
def list_products(
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    return db.query(Product).filter(
        Product.shopkeeper_id == current.id,
        Product.is_active == True
    ).all()


@router.post("/", response_model=ProductOut, status_code=201)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    product = Product(**payload.model_dump(), shopkeeper_id=current.id)
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.patch("/{product_id}", response_model=ProductOut)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.shopkeeper_id == current.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.shopkeeper_id == current.id
    ).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    product.is_active = False
    db.commit()
    return {"status": "deleted"}


@router.get("/alerts/low-stock", response_model=List[ProductOut])
def low_stock_alerts(
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    return db.query(Product).filter(
        Product.shopkeeper_id == current.id,
        Product.is_active == True,
        Product.quantity <= Product.reorder_level
    ).all()