from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_ENV: str = "development"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_INVOICE_BUCKET: str = "invoices"
    SUPABASE_AUDIO_BUCKET: str = "audio"

    # Database
    DATABASE_URL: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    # Twilio
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_WHATSAPP_FROM: str = "whatsapp:+14155238886"

    # Local fallback
    UPLOAD_DIR: str = "uploads"
    INVOICE_DIR: str = "uploads/invoices"

    @property
    def SECRET_KEY(self) -> str:
        # Use Supabase service key as JWT secret — keeps auth consistent
        return self.SUPABASE_SERVICE_KEY


settings = Settings()
