"""Pydantic response models for the dashboard API."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlatformStats(BaseModel):
    platform: str
    market_count: int
    snapshot_count: int
    snapshots_last_hour: int
    latest_snapshot_at: datetime | None


class StatsResponse(BaseModel):
    platforms: list[PlatformStats]
    total_markets: int
    total_snapshots: int


class MarketOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    platform: str
    title: str
    category: str | None
    close_time: datetime | None
    resolved: bool
    latest_yes_price: float | None
    latest_no_price: float | None
    latest_snapshot_at: datetime | None


class MarketsResponse(BaseModel):
    items: list[MarketOut]
    total: int


class TimelineBucket(BaseModel):
    bucket: datetime
    platform: str
    count: int


class TimelineResponse(BaseModel):
    buckets: list[TimelineBucket]
