"""
Supabase client setup.
- supabase_client  → uses anon key  (for normal operations)
- supabase_admin   → uses service key (for auth admin + storage)
"""
from supabase import Client, create_client

from app.config import settings

# ── Public client (anon key) ─────────────────────────────────────
supabase_client: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_ANON_KEY,
)

# ── Admin client (service role key) ─────────────────────────────
supabase_admin: Client = create_client(
    settings.SUPABASE_URL,
    settings.SUPABASE_SERVICE_KEY,
)


def get_supabase() -> Client:
    """FastAPI dependency – returns the anon client."""
    return supabase_client


def get_supabase_admin() -> Client:
    """FastAPI dependency – returns the admin client."""
    return supabase_admin
