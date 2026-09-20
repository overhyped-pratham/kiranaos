import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.config import settings
from backend.app.database import engine, Base
from backend.app.seed import seed_database
from backend.app.routers import agent, inventory, orders, webhooks

# Initialize Database Schema
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Autonomous Zero-Click Store Operator for Neighborhood Kirana Stores.",
    version=settings.VERSION
)

# CORS configuration for Frontend Dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(agent.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(webhooks.router)

@app.on_event("startup")
def startup_event():
    # Ensure database is seeded with authentic Kirana catalog
    seed_database()

@app.get("/")
def get_system_status():
    """System health and metadata endpoint."""
    return {
        "status": "online",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "connected",
        "llm_model": settings.LLM_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "reranker_model": settings.RERANKER_MODEL,
        "whatsapp_integration": "active",
        "supabase": "connected" if settings.SUPABASE_URL else "unconfigured",
        "server_time": datetime.datetime.utcnow().isoformat()
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "supabase": "connected" if settings.SUPABASE_URL else "unconfigured",
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
