"""
Unit tests for the Kalshi ingestion client.

All HTTP calls are mocked — no real API key required.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client(json_responses: list) -> MagicMock:
    """Return an async context-manager mock whose .get() returns responses in order."""
    responses = [_mock_resp(r) for r in json_responses]
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=responses)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def _mock_resp(body: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# fetch_active_markets
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_active_markets_single_page():
    from ingestion.kalshi import fetch_active_markets

    payload = {
        "markets": [
            {
                "ticker": "TEST-MARKET",
                "title": "Will X happen?",
                "category": "politics",
                "close_time": "2024-11-05T00:00:00Z",
                "status": "open",
                "result": "",
                "last_price": 55,
                "volume_24h": 1000,
            }
        ],
        "cursor": "",   # empty cursor → last page
    }

    mock_client = _make_mock_client([payload])
    with patch("ingestion.kalshi._build_client", return_value=mock_client):
        markets = await fetch_active_markets()

    assert len(markets) == 1
    m = markets[0]
    assert m.external_id == "TEST-MARKET"
    assert m.title == "Will X happen?"
    assert m.category == "politics"
    assert m.resolved is False
    assert m.resolution is None
    assert m.yes_price == pytest.approx(0.55)
    assert m.no_price == pytest.approx(0.45)
    assert m.volume_24h == 1000.0


@pytest.mark.asyncio
async def test_fetch_active_markets_cursor_pagination():
    """Two pages — verifies that the cursor loop runs until cursor is empty."""
    from ingestion.kalshi import fetch_active_markets

    page1 = {
        "markets": [{"ticker": "MKT-1", "title": "A", "status": "open",
                      "result": "", "last_price": 40}],
        "cursor": "next-page-token",
    }
    page2 = {
        "markets": [{"ticker": "MKT-2", "title": "B", "status": "open",
                      "result": "", "last_price": 60}],
        "cursor": "",
    }

    mock_client = _make_mock_client([page1, page2])
    with patch("ingestion.kalshi._build_client", return_value=mock_client):
        markets = await fetch_active_markets()

    assert len(markets) == 2
    assert markets[0].external_id == "MKT-1"
    assert markets[1].external_id == "MKT-2"
    assert mock_client.get.call_count == 2


@pytest.mark.asyncio
async def test_fetch_active_markets_resolved():
    from ingestion.kalshi import fetch_active_markets

    payload = {
        "markets": [
            {
                "ticker": "DONE-MARKET",
                "title": "Past event",
                "status": "finalized",
                "result": "yes",
                "last_price": 100,
            }
        ],
        "cursor": "",
    }

    mock_client = _make_mock_client([payload])
    with patch("ingestion.kalshi._build_client", return_value=mock_client):
        markets = await fetch_active_markets()

    assert markets[0].resolved is True
    assert markets[0].resolution == "yes"


@pytest.mark.asyncio
async def test_fetch_active_markets_http_error_returns_partial():
    """If the API errors mid-pagination, return whatever was accumulated."""
    import httpx
    from ingestion.kalshi import fetch_active_markets

    page1 = {
        "markets": [{"ticker": "MKT-1", "title": "A", "status": "open",
                      "result": "", "last_price": 50}],
        "cursor": "continue",
    }

    good_resp = _mock_resp(page1)
    bad_resp = MagicMock()
    bad_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock(status_code=500)
    )

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=[good_resp, bad_resp])
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("ingestion.kalshi._build_client", return_value=mock_client):
        markets = await fetch_active_markets()

    assert len(markets) == 1    # only the first page came through


# ---------------------------------------------------------------------------
# fetch_market_price
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_market_price_success():
    from ingestion.kalshi import fetch_market_price

    payload = {"market": {"ticker": "TEST", "last_price": 73, "volume_24h": 500}}
    mock_client = _make_mock_client([payload])

    with patch("ingestion.kalshi._build_client", return_value=mock_client):
        snap = await fetch_market_price("TEST")

    assert snap is not None
    assert snap.yes_price == pytest.approx(0.73)
    assert snap.no_price == pytest.approx(0.27)
    assert snap.volume_24h == 500.0
    assert snap.external_id == "TEST"


@pytest.mark.asyncio
async def test_fetch_market_price_404_returns_none():
    import httpx
    from ingestion.kalshi import fetch_market_price

    not_found = MagicMock()
    not_found.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock(status_code=404)
    )

    mock_client = MagicMock()
    mock_client.get = AsyncMock(return_value=not_found)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    with patch("ingestion.kalshi._build_client", return_value=mock_client):
        snap = await fetch_market_price("GONE")

    assert snap is None


# ---------------------------------------------------------------------------
# _parse_iso helper
# ---------------------------------------------------------------------------

def test_parse_iso_z_suffix():
    from ingestion.kalshi import _parse_iso

    dt = _parse_iso("2024-11-05T00:00:00Z")
    assert dt is not None
    assert dt.year == 2024
    assert dt.tzinfo is not None


def test_parse_iso_none():
    from ingestion.kalshi import _parse_iso

    assert _parse_iso(None) is None
    assert _parse_iso("") is None
