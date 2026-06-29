import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Index,
    Numeric,
    Text,
    TIMESTAMP,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector

from database import Base


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    external_id: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str | None] = mapped_column(Text)
    close_time: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)
    embedding: Mapped[list | None] = mapped_column(Vector(384))

    price_snapshots: Mapped[list["PriceSnapshot"]] = relationship(back_populates="market")

    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_markets_platform_external_id"),
    )


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    platform: Mapped[str] = mapped_column(Text, nullable=False)
    yes_price: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    no_price: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    volume_24h: Mapped[float | None] = mapped_column(Numeric)
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    market: Mapped["Market"] = relationship(back_populates="price_snapshots")

    __table_args__ = (
        Index("ix_price_snapshots_market_time", "market_id", "timestamp"),
    )


class MarketMatch(Base):
    __tablename__ = "market_matches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    kalshi_market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    polymarket_market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    similarity_score: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False)
    confirmed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    kalshi_market: Mapped["Market"] = relationship(foreign_keys=[kalshi_market_id])
    polymarket_market: Mapped["Market"] = relationship(foreign_keys=[polymarket_market_id])


class Resolution(Base):
    __tablename__ = "resolutions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    market_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("markets.id"), nullable=False)
    resolved_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    resolution: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(Text)

    market: Mapped["Market"] = relationship()


class PipelineHealth(Base):
    __tablename__ = "pipeline_health"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    service: Mapped[str] = mapped_column(Text, nullable=False)
    last_heartbeat: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    messages_received_1h: Mapped[int | None] = mapped_column(BigInteger)
