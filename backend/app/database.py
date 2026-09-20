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

db_url = settings.DATABASE_URL

# Auto-detect Supabase direct IPv6 address and translate to IPv4-compatible connection pooler
# Render, Fly.io, and Vercel cloud runtimes do not support outbound IPv6
if "db.tbaliltgyaqgffrgmtpq.supabase.co" in db_url:
    logger.info("Translating direct Supabase host to IPv4-compatible pooler host for cloud runtime...")
    db_url = db_url.replace("://postgres:", "://postgres.tbaliltgyaqgffrgmtpq:").replace(
        "db.tbaliltgyaqgffrgmtpq.supabase.co",
        "aws-0-ap-northeast-1.pooler.supabase.com"
    )

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False, "timeout": 30}
    logger.warning("WARNING: Connecting to local SQLite database: %s", db_url)
else:
    # Supabase PostgreSQL production configuration
    engine_kwargs.update({
        "pool_size": 10,
        "max_overflow": 20,
        "pool_recycle": 300
    })
    logger.info("Connecting to Supabase PostgreSQL database at: %s", db_url.split("@")[-1] if "@" in db_url else db_url)

engine = create_engine(
    db_url,
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
