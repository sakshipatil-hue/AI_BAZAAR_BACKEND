"""Reports and insights routes."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.middleware.auth import get_current_shopkeeper
from app.models import Product, Sale, Shopkeeper

router = APIRouter(prefix="/api/reports", tags=["Reports"])


@router.get("/insights")
def get_insights(
    db: Session = Depends(get_db),
    current: Shopkeeper = Depends(get_current_shopkeeper),
):
    sales = db.query(Sale).filter(Sale.shopkeeper_id == current.id).all()
    products = db.query(Product).filter(
        Product.shopkeeper_id == current.id,
        Product.is_active == True
    ).all()

    low_stock = [
        {"name": p.name, "quantity": p.quantity, "unit": p.unit}
        for p in products if p.quantity <= p.reorder_level
    ]

    total_revenue = sum(s.total for s in sales)
    top_sellers = []

    return {
        "summary": f"Total revenue: ₹{total_revenue:.2f}. You have {len(low_stock)} low stock items.",
        "top_sellers": top_sellers,
        "low_stock_items": low_stock,
        "demand_predictions": [],
        "pricing_suggestions": [],
    }