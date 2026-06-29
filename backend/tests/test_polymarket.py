"""
Unit tests for the Polymarket ingestion client.

All HTTP calls are mocked — no real credentials required.
The Gamma API is public, so the integration marker tests can hit it live.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_mock_client(json_responses: list) -> MagicMock:
    responses = [_mock_resp(r) for r in json_responses]
    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=responses)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    return mock_client


def _mock_resp(body) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = body
    resp.raise_for_status = MagicMock()
    return resp


# ---------------------------------------------------------------------------
# fetch_active_markets
# ---------------------------------------------------------------------------

SAMPLE_MARKET = {
    "conditionId": "0xabc123",
    "question": "Will Y happen by Z?",
    "category": "crypto",
    "endDate": "2024-12-01T00:00:00Z",
    "active": True,
    "resolution": None,
    "volume": 98765.0,
    # Gamma API uses parallel arrays (sometimes JSON-serialised as strings)
    "outcomes":      '["Yes", "No"]',
    "outcomePrices": '["0.72", "0.28"]',
    "clobTokenIds":  '["YES-TOKEN-ID", "NO-TOKEN-ID"]',
}


@pytest.mark.asyncio
async def test_fetch_active_markets_parses_fields():
    from ingestion.polymarket import fetch_active_markets

    # Single page — response shorter than limit (100) stops the loop
    mock_gamma = _make_mock_client([[SAMPLE_MARKET]])
    with patch("ingestion.polymarket._gamma_client", return_value=mock_gamma):
        markets = await fetch_active_markets()

    assert len(markets) == 1
    m = markets[0]
    assert m.external_id == "0xabc123"
    assert m.title == "Will Y happen by Z?"
    assert m.category == "crypto"
    assert m.resolved is False
    assert m.resolution is None
    assert m.yes_token_id == "YES-TOKEN-ID"
    assert m.no_token_id == "NO-TOKEN-ID"
    assert m.yes_price == pytest.approx(0.72)
    assert m.no_price == pytest.approx(0.28)
    assert m.volume_24h == pytest.approx(98765.0)


@pytest.mark.asyncio
async def test_fetch_active_markets_empty_tokens():
    """Markets with no tokens (e.g. closed) should not blow up."""
    from ingestion.polymarket import fetch_active_markets

    market_no_tokens = {
        "conditionId": "0xdead",
        "question": "Old market",
        "active": False,
        "outcomes":      "[]",
        "outcomePrices": "[]",
        "clobTokenIds":  "[]",
    }

    mock_gamma = _make_mock_client([[market_no_tokens]])
    with patch("ingestion.polymarket._gamma_client", return_value=mock_gamma):
        markets = await fetch_active_markets()

    assert len(markets) == 1
    m = markets[0]
    assert m.yes_token_id is None
    assert m.no_token_id is None
    assert m.yes_price is None
    assert m.no_price is None


@pytest.mark.asyncio
async def test_fetch_active_markets_pagination():
    """Full page (100 items) triggers a second request; shorter page stops."""
    from ingestion.polymarket import fetch_active_markets

    page1 = [SAMPLE_MARKET.copy() for _ in range(100)]
    page2 = [SAMPLE_MARKET.copy()]

    mock_gamma = _make_mock_client([page1, page2])
    with patch("ingestion.polymarket._gamma_client", return_value=mock_gamma):
        markets = await fetch_active_markets()

    assert len(markets) == 101
    assert mock_gamma.get.call_count == 2


# ---------------------------------------------------------------------------
# fetch_market_price
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_fetch_market_price_success():
    from ingestion.polymarket import fetch_market_price, PolymarketMarket

    market = PolymarketMarket(
        external_id="0xabc",
        title="Test",
        category=None,
        close_time=None,
        resolved=False,
        resolution=None,
        yes_token_id="YES-TOKEN-ID",
        no_token_id="NO-TOKEN-ID",
        yes_price=None,
        no_price=None,
        volume_24h=None,
    )

    mock_clob = _make_mock_client([{"mid": "0.65"}])
    with patch("ingestion.polymarket._clob_client", return_value=mock_clob):
        snap = await fetch_market_price(market)

    assert snap is not None
    assert snap.yes_price == pytest.approx(0.65)
    assert snap.no_price == pytest.approx(0.35)
    assert snap.external_id == "0xabc"


@pytest.mark.asyncio
async def test_fetch_market_price_no_token_returns_none():
    from ingestion.polymarket import fetch_market_price, PolymarketMarket

    market = PolymarketMarket(
        external_id="0xabc", title="T", category=None, close_time=None,
        resolved=False, resolution=None,
        yes_token_id=None, no_token_id=None,
        yes_price=None, no_price=None, volume_24h=None,
    )

    snap = await fetch_market_price(market)
    assert snap is None


@pytest.mark.asyncio
async def test_fetch_market_price_404_returns_none():
    import httpx
    from ingestion.polymarket import fetch_market_price, PolymarketMarket

    market = PolymarketMarket(
        external_id="0xgone", title="Gone", category=None, close_time=None,
        resolved=True, resolution="yes",
        yes_token_id="TOKEN-GONE", no_token_id=None,
        yes_price=None, no_price=None, volume_24h=None,
    )

    not_found = MagicMock()
    not_found.raise_for_status.side_effect = httpx.HTTPStatusError(
        "404", request=MagicMock(), response=MagicMock(status_code=404)
    )

    mock_clob = MagicMock()
    mock_clob.get = AsyncMock(return_value=not_found)
    mock_clob.__aenter__ = AsyncMock(return_value=mock_clob)
    mock_clob.__aexit__ = AsyncMock(return_value=None)

    with patch("ingestion.polymarket._clob_client", return_value=mock_clob):
        snap = await fetch_market_price(market)

    assert snap is None


# ---------------------------------------------------------------------------
# Live integration test (skipped by default)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.integration
async def test_live_fetch_active_markets():
    """
    Hits the real Gamma API. Run with: pytest -m integration

    Verifies that the live API returns parseable data in the expected shape.
    """
    from ingestion.polymarket import fetch_active_markets

    markets = await fetch_active_markets()

    assert len(markets) > 0, "Expected at least one active Polymarket market"
    m = markets[0]
    assert m.external_id, "external_id should be a non-empty string"
    assert m.title, "title should be non-empty"
    # Prices are optional if tokens list was empty, but most active markets have them
    if m.yes_price is not None:
        assert 0.0 <= m.yes_price <= 1.0
        assert 0.0 <= m.no_price <= 1.0
