import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = FastAPI(
    title="ChargebackGuard API",
    description="Explainable AI Risk & Fraud Detection Agent API",
    version="1.0.0"
)

# Configure CORS explicitly for frontend origin (port 5173 default for Vite)
origins_str = os.getenv("CORS_ORIGINS", "http://localhost:5173")
origins = [origin.strip() for origin in origins_str.split(",") if origin.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ChargebackGuard API",
        "version": "1.0.0"
    }
