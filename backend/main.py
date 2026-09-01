import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from app.database import Base, engine
from app.routers import batches, transactions


# Load environment variables
load_dotenv()

# Create SQLite database tables on startup
Base.metadata.create_all(bind=engine)

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
app.include_router(batches.router)
app.include_router(transactions.router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ChargebackGuard API",
        "version": "1.0.0"
    }
