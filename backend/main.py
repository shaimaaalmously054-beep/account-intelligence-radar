"""
Account Intelligence Radar - FastAPI Backend
Averroa Assignment | Author: Mazen Zawal
"""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Load .env — try backend/ first, then project root.
# Works regardless of which directory uvicorn is launched from.
# ---------------------------------------------------------------------------
_here = Path(__file__).parent
load_dotenv(_here / ".env")          # backend/.env  (takes precedence)
load_dotenv(_here.parent / ".env")   # project root .env

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import jobs

# ---------------------------------------------------------------------------
# Logging (OWASP: no secrets / sensitive payloads in logs)
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Account Intelligence Radar API starting up")
    os.makedirs("reports", exist_ok=True)

    # Validate API keys at startup — log presence only, never values
    required = {
        "SERPAPI_KEY":       os.getenv("SERPAPI_KEY"),
        "FIRECRAWL_API_KEY": os.getenv("FIRECRAWL_API_KEY"),
    }
    optional = {
        "DEEPSEEK_API_KEY": os.getenv("DEEPSEEK_API_KEY"),
        "OPENAI_API_KEY":   os.getenv("OPENAI_API_KEY"),
    }
    missing = [k for k, v in required.items() if not v]
    if missing:
        logger.error("MISSING required API keys: %s — check your .env file", missing)
    else:
        logger.info("Required API keys: all present")

    llm_keys = [k for k, v in optional.items() if v]
    if llm_keys:
        logger.info("LLM keys available: %s", llm_keys)
    else:
        logger.warning(
            "No LLM keys set (DEEPSEEK_API_KEY / OPENAI_API_KEY) — "
            "URL selection will fall back to top-5 SERP results"
        )

    yield
    logger.info("Account Intelligence Radar API shutting down")


app = FastAPI(
    title="Account Intelligence Radar",
    description="Pipeline generation infrastructure for business outreach.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "account-intelligence-radar"}
