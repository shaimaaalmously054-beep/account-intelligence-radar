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

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import auth, intelligence, jobs
from services.database import init_db

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
    init_db()

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

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000"
    ).split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(intelligence.router, prefix="/api", tags=["intelligence"])


@app.get("/health")
async def health():
    return {"status": "ok", "service": "account-intelligence-radar"}


_frontend = _here.parent / "frontend"
if _frontend.exists():
    @app.get("/")
    async def frontend_index():
        return FileResponse(_frontend / "index.html")

    @app.get("/{path:path}")
    async def frontend_routes(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "API route not found")
        return FileResponse(_frontend / "index.html")
