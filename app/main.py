from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI

from app.cache import cache
from app.config import get_settings
from app.db import Base, engine
from app.routers import auth, manage, sdk


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    if settings.sentry_dsn:
        sentry_sdk.init(dsn=settings.sentry_dsn, traces_sample_rate=0.1, send_default_pii=False)
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="Beacon", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(manage.router)
app.include_router(sdk.router)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "cache": type(cache).__name__}
