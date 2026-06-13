from fastapi import FastAPI

app = FastAPI(title="EdgeFinder", version="0.1.0")


@app.get("/health")
async def health():
    # TODO: return a dict with:
    #   - status: "ok"
    #   - db: whether postgres is reachable (try a simple SELECT 1 via get_db)
    #   - environment: from settings
    # For now, return the bare minimum to get the server running
    return {"status": "ok"}


# TODO: add startup/shutdown event handlers using @app.on_event or lifespan
# On startup you'll want to:
#   1. Run any pending Alembic migrations (optional — can do manually)
#   2. Start the WebSocket ingestion tasks (Steps 0.2, 0.3)
#   3. Start the APScheduler (Step 0.5)
