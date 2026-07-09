from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.dashboard import router as dashboard_router
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

# Dashboard is a read-only debugging tool with no auth yet — fine while the
# API is only reachable by you, but tighten this before anyone else gets the URL.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(dashboard_router)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.environment}
