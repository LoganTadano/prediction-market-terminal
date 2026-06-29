from contextlib import asynccontextmanager

from fastapi import FastAPI

from config import settings
from ingestion.scheduler import scheduler, register_jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    register_jobs(interval_minutes=5)
    scheduler.start()

    yield

    if scheduler.running:
        scheduler.shutdown()


app = FastAPI(title="EdgeFinder", version="0.1.0", lifespan=lifespan)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}
