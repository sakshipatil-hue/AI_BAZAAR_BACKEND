"""
Auth middleware using Supabase Auth.
- Register/Login handled via Supabase Auth API
- JWT tokens issued by Supabase
- We verify tokens using Supabase admin client
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from supabase import Client

from app.supabase_client import get_supabase_admin
from app.database import get_db
from app.models import Shopkeeper
from sqlalchemy.orm import Session

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_shopkeeper(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    admin: Client = Depends(get_supabase_admin),
) -> Shopkeeper:
    """
    Verify Supabase JWT token and return the matching shopkeeper.
    """
    try:
        # Verify token with Supabase
        user_response = admin.auth.get_user(token)
        supabase_user = user_response.user

        if not supabase_user:
            raise HTTPException(status_code=401, detail="Invalid token")

        # Look up shopkeeper by supabase_uid
        shopkeeper = db.query(Shopkeeper).filter(
            Shopkeeper.supabase_uid == supabase_user.id
        ).first()

        if not shopkeeper:
            raise HTTPException(status_code=401, detail="Shopkeeper not found")

        if not shopkeeper.is_active:
            raise HTTPException(status_code=401, detail="Account is inactive")

        return shopkeeper

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
