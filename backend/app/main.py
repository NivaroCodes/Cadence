import base64
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

def init_persistent_secrets():
    data_dir = Path(os.getenv("PERSISTENT_DATA_DIR", "./"))
    data_dir.mkdir(parents=True, exist_ok=True)
    
    creds_b64 = os.getenv("GMAIL_CREDENTIALS_B64")
    creds_path = Path(os.getenv("GMAIL_CREDENTIALS_PATH", "./credentials.json"))
    if creds_b64 and not creds_path.exists():
        creds_path.write_bytes(base64.b64decode(creds_b64))

    token_b64 = os.getenv("GMAIL_TOKEN_B64")
    token_path = Path(os.getenv("GMAIL_TOKEN_PATH", "./token.pickle"))
    if token_b64 and not token_path.exists():
        token_path.write_bytes(base64.b64decode(token_b64))

init_persistent_secrets()

from app.config import settings
from app.database import AsyncSessionLocal, engine
from app.routers import auth, campaigns, leads

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Cadence API [env=%s]", settings.APP_ENV)
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    logger.info("Database connection verified")
    await start_scheduler()
    yield
    await stop_scheduler()
    await engine.dispose()
    logger.info("Engine disposed, shutdown complete")


app = FastAPI(
    title="Cadence API",
    description="AI-powered sales automation backend",
    version="0.1.0",
    docs_url="/docs" if settings.APP_ENV == "dev" else None,
    redoc_url=None,
    lifespan=lifespan,
)

_cors_origins = (
    ["*"] if settings.APP_ENV == "dev"
    else ["https://cadence.app"]
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(leads.router, prefix="/api/v1/leads", tags=["leads"])
app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])


@app.get("/health", tags=["infra"])
async def health_check() -> dict[str, str]:
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok", "env": settings.APP_ENV}
