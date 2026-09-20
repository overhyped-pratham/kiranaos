from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from backend.app.config import settings

import logging

logger = logging.getLogger("kiranaos.database")

# Configure engine based on database dialect
connect_args = {}
engine_kwargs = {
    "echo": False,
    "pool_pre_ping": True
}

if settings.DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
    logger.warning("WARNING: Connecting to local SQLite database: %s", settings.DATABASE_URL)
else:
    # Supabase PostgreSQL production configuration
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300
    })
    logger.info("Connecting to Supabase PostgreSQL database at: %s", settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
