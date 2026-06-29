"""
DB write helpers for ingested market data.

All functions take an AsyncSession and commit nothing — the caller decides
when to commit. This keeps transaction control explicit and lets the scheduler
batch a full cycle in one transaction.
"""

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert as pg_insert

from models import Market, PriceSnapshot
from ingestion.kalshi import KalshiMarket
from ingestion.polymarket import PolymarketMarket

logger = logging.getLogger(__name__)


async def upsert_kalshi_market(db: AsyncSession, market: KalshiMarket) -> Market:
    """
    Insert a Kalshi market or update mutable fields if it already exists.

    Uses PostgreSQL INSERT ... ON CONFLICT DO UPDATE so one round-trip handles
    both the insert and update case. The uniqueness key is the constraint
    uq_markets_platform_external_id defined in models.py.

    Fields that never change (id, created_at) are NOT in the set_ dict —
    ON CONFLICT only touches what we list there.
    """
    stmt = pg_insert(Market).values(
        platform="kalshi",
        external_id=market.external_id,
        title=market.title,
        category=market.category,
        close_time=market.close_time,
        resolved=market.resolved,
        resolution=market.resolution,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_markets_platform_external_id",
        set_={
            "title": stmt.excluded.title,
            "category": stmt.excluded.category,
            "close_time": stmt.excluded.close_time,
            "resolved": stmt.excluded.resolved,
            "resolution": stmt.excluded.resolution,
        },
    )
    await db.execute(stmt)

    result = await db.execute(
        select(Market).where(
            Market.platform == "kalshi",
            Market.external_id == market.external_id,
        )
    )
    return result.scalar_one()


async def upsert_polymarket_market(db: AsyncSession, market: PolymarketMarket) -> Market:
    """
    Insert a Polymarket market or update mutable fields if it already exists.

    Same upsert pattern as upsert_kalshi_market — just a different platform
    value and source dataclass.
    """
    stmt = pg_insert(Market).values(
        platform="polymarket",
        external_id=market.external_id,
        title=market.title,
        category=market.category,
        close_time=market.close_time,
        resolved=market.resolved,
        resolution=market.resolution,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_markets_platform_external_id",
        set_={
            "title": stmt.excluded.title,
            "category": stmt.excluded.category,
            "close_time": stmt.excluded.close_time,
            "resolved": stmt.excluded.resolved,
            "resolution": stmt.excluded.resolution,
        },
    )
    await db.execute(stmt)

    result = await db.execute(
        select(Market).where(
            Market.platform == "polymarket",
            Market.external_id == market.external_id,
        )
    )
    return result.scalar_one()


async def insert_price_snapshot(
    db: AsyncSession,
    market_id,
    platform: str,
    yes_price: float,
    no_price: float,
    volume_24h: float | None,
    timestamp: datetime,
) -> PriceSnapshot:
    """
    Append a new price snapshot row.

    Snapshots are append-only: every ingestion cycle adds a new row.
    The composite index on (market_id, timestamp) defined in models.py
    makes time-series range queries fast.
    """
    snapshot = PriceSnapshot(
        market_id=market_id,
        platform=platform,
        yes_price=yes_price,
        no_price=no_price,
        volume_24h=volume_24h,
        timestamp=timestamp,
    )
    db.add(snapshot)
    await db.flush()
    return snapshot
