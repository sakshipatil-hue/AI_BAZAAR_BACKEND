"""AI Bazaar — FastAPI entry point with Supabase integration."""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import Base, engine
import app.models  # noqa

from app.routes import auth, inventory, reports, sales, scan, voice, whatsapp
from app.services.storage import ensure_buckets_exist

# ── Create DB tables ──────────────────────────────────────────────
Base.metadata.create_all(bind=engine)

# ── Ensure local dirs exist ───────────────────────────────────────
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.INVOICE_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "audio"), exist_ok=True)

# ── Ensure Supabase storage buckets exist ────────────────────────
ensure_buckets_exist()

# ── FastAPI app ───────────────────────────────────────────────────
app = FastAPI(
    title="AI Bazaar API",
    description="Voice-first AI assistant for Indian shopkeepers — powered by Supabase",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── CORS ──────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ai-bazaar-zeta.vercel.app", "http://localhost:5500"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files ──────────────────────────────────────────────────
app.mount("/static", StaticFiles(directory=settings.UPLOAD_DIR), name="static")

# ── Routers ───────────────────────────────────────────────────────
app.include_router(auth.router)
app.include_router(inventory.router)
app.include_router(sales.router)
app.include_router(voice.router)
app.include_router(scan.router)
app.include_router(reports.router)
app.include_router(whatsapp.router)


@app.get("/health", tags=["Health"])
def health():
    return {
        "status": "ok",
        "app": "AI Bazaar",
        "version": "2.0.0",
        "database": "Supabase PostgreSQL",
        "storage": "Supabase Storage",
        "auth": "Supabase Auth",
    }
