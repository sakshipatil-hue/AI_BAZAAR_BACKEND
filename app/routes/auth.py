"""
Auth routes — Register & Login using Supabase Auth.
Supabase handles password hashing and JWT token generation.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from supabase import Client

from app.database import get_db
from app.middleware.auth import get_current_shopkeeper
from app.models import Shopkeeper
from app.schemas import LoginRequest, ShopkeeperCreate, ShopkeeperOut, Token
from app.supabase_client import get_supabase_admin

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=ShopkeeperOut, status_code=201)
def register(
    payload: ShopkeeperCreate,
    db: Session = Depends(get_db),
    admin: Client = Depends(get_supabase_admin),
):
    # Check phone not already used
    if db.query(Shopkeeper).filter(Shopkeeper.phone == payload.phone).first():
        raise HTTPException(status_code=400, detail="Phone number already registered")

    # Register with Supabase Auth
    email = payload.email or f"{payload.phone}@aibazaar.app"
    try:
        auth_response = admin.auth.admin.create_user({
            "email": email,
            "password": payload.password,
            "email_confirm": True,   # skip email verification
        })
        supabase_uid = auth_response.user.id
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Auth registration failed: {str(e)}")

    # Save shopkeeper profile in our DB
    shopkeeper = Shopkeeper(
        supabase_uid=supabase_uid,
        name=payload.name,
        phone=payload.phone,
        email=email,
        whatsapp_number=payload.whatsapp_number or payload.phone,
        shop_name=payload.shop_name,
        gst_number=payload.gst_number,
        language=payload.language,
    )
    db.add(shopkeeper)
    db.commit()
    db.refresh(shopkeeper)
    return shopkeeper


@router.post("/login", response_model=Token)
def login(
    payload: LoginRequest,
    db: Session = Depends(get_db),
    admin: Client = Depends(get_supabase_admin),
):
    # Find shopkeeper by phone
    shopkeeper = db.query(Shopkeeper).filter(Shopkeeper.phone == payload.phone).first()
    if not shopkeeper:
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    # Sign in with Supabase Auth using email derived from phone
    email = shopkeeper.email or f"{payload.phone}@aibazaar.app"
    try:
        from app.supabase_client import supabase_client
        auth_response = supabase_client.auth.sign_in_with_password({
            "email": email,
            "password": payload.password,
        })
        token = auth_response.session.access_token
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid phone or password")

    return {"access_token": token, "token_type": "bearer"}


@router.get("/me", response_model=ShopkeeperOut)
def get_me(current: Shopkeeper = Depends(get_current_shopkeeper)):
    return current
