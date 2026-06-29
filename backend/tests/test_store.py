"""
Unit tests for the DB store helpers.

The AsyncSession is mocked so these run without a real database.
They verify that the right SQL operations are called with the right arguments.
"""

import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch, call


def _make_db(scalar_return=None) -> AsyncMock:
    """Return a mock AsyncSession whose execute() and flush() are async."""
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = scalar_return
    db.execute = AsyncMock(return_value=mock_result)
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


# ---------------------------------------------------------------------------
# insert_price_snapshot
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_price_snapshot_adds_and_flushes():
    from ingestion.store import insert_price_snapshot
    from models import PriceSnapshot

    db = _make_db()
    market_id = uuid.uuid4()
    ts = datetime.now(timezone.utc)

    snap = await insert_price_snapshot(
        db,
        market_id=market_id,
        platform="kalshi",
        yes_price=0.55,
        no_price=0.45,
        volume_24h=1234.0,
        timestamp=ts,
    )

    db.add.assert_called_once()
    db.flush.assert_awaited_once()

    added = db.add.call_args[0][0]
    assert isinstance(added, PriceSnapshot)
    assert added.market_id == market_id
    assert added.platform == "kalshi"
    assert float(added.yes_price) == pytest.approx(0.55)
    assert float(added.no_price) == pytest.approx(0.45)
    assert float(added.volume_24h) == pytest.approx(1234.0)
    assert added.timestamp == ts


@pytest.mark.asyncio
async def test_insert_price_snapshot_none_volume():
    from ingestion.store import insert_price_snapshot

    db = _make_db()
    await insert_price_snapshot(
        db, market_id=uuid.uuid4(), platform="polymarket",
        yes_price=0.3, no_price=0.7, volume_24h=None,
        timestamp=datetime.now(timezone.utc),
    )

    added = db.add.call_args[0][0]
    assert added.volume_24h is None


# ---------------------------------------------------------------------------
# upsert_kalshi_market
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_kalshi_market_executes_and_selects():
    """
    Verify that upsert issues two DB calls: execute(insert) + execute(select),
    and returns whatever scalar_one() returns.
    """
    from ingestion.store import upsert_kalshi_market
    from ingestion.kalshi import KalshiMarket
    from models import Market

    fake_market = Market()
    fake_market.id = uuid.uuid4()
    fake_market.platform = "kalshi"
    fake_market.external_id = "TEST-TICKER"

    db = _make_db(scalar_return=fake_market)

    km = KalshiMarket(
        external_id="TEST-TICKER",
        title="Test Market",
        category="politics",
        close_time=None,
        resolved=False,
        resolution=None,
        yes_price=0.6,
        no_price=0.4,
        volume_24h=500.0,
    )

    result = await upsert_kalshi_market(db, km)

    assert db.execute.await_count == 2   # insert + select
    assert result is fake_market


# ---------------------------------------------------------------------------
# upsert_polymarket_market
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_polymarket_market_executes_and_selects():
    from ingestion.store import upsert_polymarket_market
    from ingestion.polymarket import PolymarketMarket
    from models import Market

    fake_market = Market()
    fake_market.id = uuid.uuid4()
    fake_market.platform = "polymarket"
    fake_market.external_id = "0xabc123"

    db = _make_db(scalar_return=fake_market)

    pm = PolymarketMarket(
        external_id="0xabc123",
        title="Poly Test",
        category="crypto",
        close_time=None,
        resolved=False,
        resolution=None,
        yes_token_id="Y",
        no_token_id="N",
        yes_price=0.72,
        no_price=0.28,
        volume_24h=None,
    )

    result = await upsert_polymarket_market(db, pm)

    assert db.execute.await_count == 2
    assert result is fake_market
