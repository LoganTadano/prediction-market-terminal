"""
APScheduler setup for periodic ingestion jobs.

Uses AsyncIOScheduler so it shares FastAPI's event loop — no thread overhead.
Jobs run on a fixed interval; both platforms are polled independently so a
slow Kalshi response doesn't block Polymarket and vice versa.
"""

import logging
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from database import AsyncSessionLocal
import ingestion.kalshi as kalshi
import ingestion.polymarket as polymarket
from ingestion.store import (
    upsert_kalshi_market,
    upsert_polymarket_market,
    insert_price_snapshot,
)

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def ingest_kalshi() -> None:
    """
    Full Kalshi ingestion cycle.

    Fetches all active markets (prices included in the list response),
    upserts market rows, then appends one price snapshot per market.
    Everything commits in a single transaction at the end.
    """
    logger.info("Kalshi ingestion cycle starting")
    try:
        markets = await kalshi.fetch_active_markets()
        snap_count = 0
        now = datetime.utcnow()

        async with AsyncSessionLocal() as db:
            for market in markets:
                market_row = await upsert_kalshi_market(db, market)

                if market.yes_price is not None and market.no_price is not None:
                    await insert_price_snapshot(
                        db,
                        market_id=market_row.id,
                        platform="kalshi",
                        yes_price=market.yes_price,
                        no_price=market.no_price,
                        volume_24h=market.volume_24h,
                        timestamp=now,
                    )
                    snap_count += 1

            await db.commit()

        logger.info(
            "Kalshi: upserted %d markets, stored %d snapshots", len(markets), snap_count
        )
    except Exception:
        logger.exception("Kalshi ingestion cycle failed")


async def ingest_polymarket() -> None:
    """
    Full Polymarket ingestion cycle.

    Same pattern as ingest_kalshi. Prices come from the Gamma API's
    tokens[].price field — no separate CLOB call needed in the bulk path.
    """
    logger.info("Polymarket ingestion cycle starting")
    try:
        markets = await polymarket.fetch_active_markets()
        snap_count = 0
        now = datetime.utcnow()

        async with AsyncSessionLocal() as db:
            for market in markets:
                market_row = await upsert_polymarket_market(db, market)

                if market.yes_price is not None and market.no_price is not None:
                    await insert_price_snapshot(
                        db,
                        market_id=market_row.id,
                        platform="polymarket",
                        yes_price=market.yes_price,
                        no_price=market.no_price,
                        volume_24h=market.volume_24h,
                        timestamp=now,
                    )
                    snap_count += 1

            await db.commit()

        logger.info(
            "Polymarket: upserted %d markets, stored %d snapshots", len(markets), snap_count
        )
    except Exception:
        logger.exception("Polymarket ingestion cycle failed")


def register_jobs(interval_minutes: int = 5) -> None:
    """
    Register ingestion jobs with the scheduler.

    Both jobs use next_run_time=now so they fire immediately on startup
    rather than waiting one full interval before the first run.
    """
    scheduler.add_job(
        ingest_kalshi,
        trigger="interval",
        minutes=interval_minutes,
        id="kalshi_ingestion",
        replace_existing=True,
        next_run_time=datetime.utcnow(),
    )
    scheduler.add_job(
        ingest_polymarket,
        trigger="interval",
        minutes=interval_minutes,
        id="polymarket_ingestion",
        replace_existing=True,
        next_run_time=datetime.utcnow(),
    )
    logger.info(
        "Registered Kalshi + Polymarket ingestion jobs (every %d min)", interval_minutes
    )
