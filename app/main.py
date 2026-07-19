import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import chatwoot_webhook, meta_webhook

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Comentarios IG -> Chatwoot", lifespan=lifespan)
app.include_router(meta_webhook.router)
app.include_router(chatwoot_webhook.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
