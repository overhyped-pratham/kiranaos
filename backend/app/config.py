import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from the backend root
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

class Settings:
    PROJECT_NAME: str = "KiranaOS — Zero-Click Store Operator"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./kiranaos.db")
    
    # AI Models
    HUGGINGFACE_API_KEY: str = os.getenv("HUGGINGFACE_API_KEY", "")
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "auto")
    
    LLM_MODEL: str = "Qwen/Qwen2.5-3B-Instruct"
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
    RERANKER_MODEL: str = os.getenv("RERANKER_MODEL", "BAAI/bge-reranker-v2-m3")
    
    # n8n & Automations
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/kiranaos-order")
    N8N_ALERT_WEBHOOK_URL: str = os.getenv("N8N_ALERT_WEBHOOK_URL", "http://localhost:5678/webhook/kiranaos-low-stock")
    DELIVERY_WEBHOOK_URL: str = os.getenv("DELIVERY_WEBHOOK_URL", "http://localhost:8000/webhook/delivery-mock")
    
    # WhatsApp Cloud API
    WHATSAPP_VERIFY_TOKEN: str = os.getenv("WHATSAPP_VERIFY_TOKEN", "kiranaos_secret_token_2026")
    WHATSAPP_ACCESS_TOKEN: str = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    WHATSAPP_PHONE_NUMBER_ID: str = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
    MERCHANT_PHONE: str = os.getenv("MERCHANT_PHONE", "+919876543210")

    # Supabase Integration
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_PUBLISHABLE_KEY: str = os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    SUPABASE_SECRET_KEY: str = os.getenv("SUPABASE_SECRET_KEY", "")
    SUPABASE_JWKS_URL: str = os.getenv("SUPABASE_JWKS_URL", "")

    # Business Rules
    DEFAULT_DELIVERY_CHARGE: float = 20.0
    FREE_DELIVERY_THRESHOLD: float = 500.0
    HIGH_VALUE_APPROVAL_THRESHOLD: float = 2500.0
    HIGH_QUANTITY_APPROVAL_THRESHOLD: int = 15

settings = Settings()
