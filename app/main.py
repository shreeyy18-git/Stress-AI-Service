"""
FastAPI application entry point.

Start with:
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
"""

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.routes.chat import router as chat_router
from app.routes.summary import router as summary_router

# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan (startup / shutdown hooks)
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI microservice starting up…")
    logger.info("   Model  : %s", os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"))
    logger.info("   Service is ready to handle requests.")
    yield
    logger.info("🛑 AI microservice shutting down…")


# ---------------------------------------------------------------------------
# App instance
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Stress & Safety AI Microservice",
    description=(
        "Analyzes user messages for emotion, risk, and stress. "
        "Generates empathetic responses and daily summaries using Gemini."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ---------------------------------------------------------------------------
# CORS — adjust origins in production
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Tighten this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(chat_router, tags=["Chat Analysis"])
app.include_router(summary_router, tags=["Daily Summary"])

# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/", tags=["Health"])
async def root():
    return JSONResponse({"status": "ok", "service": "Stress & Safety AI Microservice"})


@app.get("/health", tags=["Health"])
async def health():
    return JSONResponse(
        {
            "status": "healthy",
            "model": os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite"),
        }
    )
