import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import Base, engine, SessionLocal
from app.routers import batches, transactions, auth, metrics, config
from app.auth import seed_demo_users

# Load environment variables
load_dotenv()

# Create SQLite database tables on startup
Base.metadata.create_all(bind=engine)

# Seed demo users on startup
db = SessionLocal()
try:
    seed_demo_users(db)
finally:
    db.close()

app = FastAPI(
    title="ChargebackGuard API",
    description="Explainable AI Risk & Fraud Detection Agent API",
    version="1.0.0"
)

# Configure CORS explicitly for frontend origin
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(batches.router)
app.include_router(transactions.router)
app.include_router(metrics.router)
app.include_router(config.router)

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ChargebackGuard API",
        "version": "1.0.0"
    }
