import logging
from typing import Optional
from supabase import create_client, Client
from backend.app.config import settings

logger = logging.getLogger("kiranaos.supabase")

_client: Optional[Client] = None

def get_supabase_client() -> Optional[Client]:
    """
    Returns a singleton Supabase client using configured credentials.
    Falls back gracefully if Supabase credentials are not provided.
    """
    global _client
    if _client is not None:
        return _client

    if not settings.SUPABASE_URL:
        logger.warning("SUPABASE_URL is not configured; Supabase client unavailable.")
        return None

    # Prefer Secret Key for backend operations, fallback to Publishable Key
    key = settings.SUPABASE_SECRET_KEY or settings.SUPABASE_PUBLISHABLE_KEY
    if not key:
        logger.warning("Neither SUPABASE_SECRET_KEY nor SUPABASE_PUBLISHABLE_KEY is configured.")
        return None

    try:
        _client = create_client(settings.SUPABASE_URL, key)
        logger.info(f"Supabase client initialized successfully for project: {settings.SUPABASE_URL}")
        return _client
    except Exception as e:
        logger.error(f"Failed to initialize Supabase client: {e}")
        return None
