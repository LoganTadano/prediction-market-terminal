"""
Read-only endpoints backing the ingestion dashboard.

These exist to answer one question: "is data actually flowing in?" Nothing
here writes to the database. All queries run directly against Market and
PriceSnapshot — PipelineHealth isn't populated yet (no writer wired up), so
freshness is derived from PriceSnapshot.timestamp instead.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    MarketOut,
    MarketsResponse,
    PlatformStats,
    StatsResponse,
    TimelineBucket,
    TimelineResponse,
)
from database import get_db
from models import Market, PriceSnapshot

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: AsyncSession = Depends(get_db)) -> StatsResponse:
    """Per-platform market/snapshot counts plus last-hour ingestion activity."""
    market_counts = dict(
        (row.platform, row.count)
        for row in (
            await db.execute(
                select(Market.platform, func.count(Market.id).label("count")).group_by(
                    Market.platform
                )
            )
        ).all()
    )
    snapshot_counts = dict(
        (row.platform, row.count)
        for row in (
            await db.execute(
                select(
                    PriceSnapshot.platform, func.count(PriceSnapshot.id).label("count")
                ).group_by(PriceSnapshot.platform)
            )
        ).all()
    )
    latest_snapshot = dict(
        (row.platform, row.latest)
        for row in (
            await db.execute(
                select(
                    PriceSnapshot.platform,
                    func.max(PriceSnapshot.timestamp).label("latest"),
                ).group_by(PriceSnapshot.platform)
            )
        ).all()
    )
    since = datetime.utcnow() - timedelta(hours=1)
    last_hour_counts = dict(
        (row.platform, row.count)
        for row in (
            await db.execute(
                select(
                    PriceSnapshot.platform, func.count(PriceSnapshot.id).label("count")
                )
                .where(PriceSnapshot.timestamp >= since)
                .group_by(PriceSnapshot.platform)
            )
        ).all()
    )

    platforms = sorted(set(market_counts) | set(snapshot_counts))
    stats = [
        PlatformStats(
            platform=platform,
            market_count=market_counts.get(platform, 0),
            snapshot_count=snapshot_counts.get(platform, 0),
            snapshots_last_hour=last_hour_counts.get(platform, 0),
            latest_snapshot_at=latest_snapshot.get(platform),
        )
        for platform in platforms
    ]

    return StatsResponse(
        platforms=stats,
        total_markets=sum(market_counts.values()),
        total_snapshots=sum(snapshot_counts.values()),
    )


@router.get("/markets", response_model=MarketsResponse)
async def list_markets(
    platform: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> MarketsResponse:
    """
    Recently-created markets with their most recent price snapshot.

    The latest price is fetched with a correlated scalar subquery (one row
    per market, ordered by timestamp desc, limit 1) rather than a join —
    simpler than DISTINCT ON and reads clearly for a low-traffic endpoint.
    """

    def latest(column):
        return (
            select(column)
            .where(PriceSnapshot.market_id == Market.id)
            .order_by(PriceSnapshot.timestamp.desc())
            .limit(1)
            .correlate(Market)
            .scalar_subquery()
        )

    stmt = select(
        Market.id,
        Market.platform,
        Market.title,
        Market.category,
        Market.close_time,
        Market.resolved,
        latest(PriceSnapshot.yes_price).label("latest_yes_price"),
        latest(PriceSnapshot.no_price).label("latest_no_price"),
        latest(PriceSnapshot.timestamp).label("latest_snapshot_at"),
    ).order_by(Market.created_at.desc())

    count_stmt = select(func.count()).select_from(Market)

    if platform:
        stmt = stmt.where(Market.platform == platform)
        count_stmt = count_stmt.where(Market.platform == platform)
    if search:
        pattern = f"%{search}%"
        stmt = stmt.where(Market.title.ilike(pattern))
        count_stmt = count_stmt.where(Market.title.ilike(pattern))

    total = (await db.execute(count_stmt)).scalar_one()
    rows = (await db.execute(stmt.limit(limit).offset(offset))).all()

    return MarketsResponse(
        items=[MarketOut.model_validate(row._mapping) for row in rows],
        total=total,
    )


@router.get("/ingestion-timeline", response_model=TimelineResponse)
async def get_ingestion_timeline(
    hours: int = Query(default=24, le=168),
    db: AsyncSession = Depends(get_db),
) -> TimelineResponse:
    """
    Snapshot counts per platform, bucketed by hour, for the last N hours.

    Hour-granularity buckets are coarse for a 5-minute polling interval
    (~12 snapshots/bucket/platform) but keep the query and chart simple.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    bucket = func.date_trunc("hour", PriceSnapshot.timestamp)

    stmt = (
        select(
            bucket.label("bucket"),
            PriceSnapshot.platform,
            func.count(PriceSnapshot.id).label("count"),
        )
        .where(PriceSnapshot.timestamp >= since)
        .group_by(bucket, PriceSnapshot.platform)
        .order_by(bucket)
    )
    rows = (await db.execute(stmt)).all()

    return TimelineResponse(
        buckets=[
            TimelineBucket(bucket=row.bucket, platform=row.platform, count=row.count)
            for row in rows
        ]
    )
