"""
Polymarket ingestion client.

Gamma API — market metadata + spot prices
  https://gamma-api.polymarket.com/markets
CLOB API  — real-time order-book midpoints (used for on-demand refresh)
  https://clob.polymarket.com/

Polymarket binary markets have two ERC-1155 token IDs (YES / NO).
Prices from Gamma are already 0-1 floats.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import json
import httpx

logger = logging.getLogger(__name__)

GAMMA_URL = "https://gamma-api.polymarket.com"
CLOB_URL  = "https://clob.polymarket.com"


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class PolymarketMarket:
    external_id: str           # condition_id hex string
    title: str
    category: str | None
    close_time: datetime | None
    resolved: bool
    resolution: str | None
    yes_token_id: str | None   # needed for CLOB on-demand refresh
    no_token_id: str | None
    # Gamma includes spot prices in the tokens list — use them directly
    yes_price: float | None
    no_price: float | None
    volume_24h: float | None


@dataclass
class PolymarketSnapshot:
    external_id: str
    yes_price: float
    no_price: float
    volume_24h: float | None
    timestamp: datetime


def _gamma_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=GAMMA_URL,
        headers={"Accept": "application/json"},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )


def _clob_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=CLOB_URL,
        headers={"Accept": "application/json"},
        timeout=httpx.Timeout(10.0, connect=5.0),
    )


async def fetch_active_markets() -> list[PolymarketMarket]:
    """
    Fetch all active Polymarket markets via the Gamma API (offset pagination).

    Prices are extracted from the `tokens[].price` field so that the
    scheduler can build snapshots without additional CLOB calls.
    """
    markets: list[PolymarketMarket] = []
    limit = 100
    offset = 0

    async with _gamma_client() as client:
        while True:
            try:
                resp = await client.get("/markets", params={
                    "active": "true",
                    "closed": "false",
                    "limit": limit,
                    "offset": offset,
                })
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("Polymarket GET /markets failed: %s", exc)
                break

            page = resp.json()
            if not isinstance(page, list):
                logger.error("Unexpected Polymarket response shape: %s", type(page))
                break

            for m in page:
                # Gamma API double-serializes these fields as JSON strings inside JSON
                def _p(v):
                    if isinstance(v, list): return v
                    try: return json.loads(v) if v else []
                    except Exception: return []
                outcomes       = _p(m.get("outcomes"))
                outcome_prices = _p(m.get("outcomePrices"))
                clob_ids       = _p(m.get("clobTokenIds"))

                try:
                    yes_idx = outcomes.index("Yes")
                    no_idx  = outcomes.index("No")
                    yes_token_id  = clob_ids[yes_idx]       if yes_idx < len(clob_ids)       else None
                    no_token_id   = clob_ids[no_idx]        if no_idx  < len(clob_ids)       else None
                    yes_price_raw = outcome_prices[yes_idx] if yes_idx < len(outcome_prices) else None
                    no_price_raw  = outcome_prices[no_idx]  if no_idx  < len(outcome_prices) else None
                except ValueError:
                    yes_token_id = no_token_id = yes_price_raw = no_price_raw = None

                vol_raw = m.get("volume")

                markets.append(PolymarketMarket(
                    external_id=m.get("conditionId", ""),
                    title=m.get("question", ""),
                    category=m.get("category"),
                    close_time=_parse_iso(m.get("endDate")),
                    resolved=not m.get("active", True),
                    resolution=m.get("resolution"),
                    yes_token_id=yes_token_id,
                    no_token_id=no_token_id,
                    yes_price=float(str(yes_price_raw).strip()) if yes_price_raw and str(yes_price_raw).strip() else None,
                    no_price=float(str(no_price_raw).strip()) if no_price_raw and str(no_price_raw).strip() else None,
                    volume_24h=float(vol_raw) if vol_raw is not None else None,
                ))

            if len(page) < limit:
                break
            offset += limit

    logger.info("Polymarket: fetched %d active markets", len(markets))
    return markets


async def fetch_market_price(market: PolymarketMarket) -> PolymarketSnapshot | None:
    """
    Fetch a real-time midpoint for a single Polymarket market via the CLOB API.

    Use this for on-demand refresh; the bulk path uses prices already present
    in the PolymarketMarket object from fetch_active_markets.
    """
    if market.yes_token_id is None:
        return None

    async with _clob_client() as client:
        try:
            resp = await client.get("/midpoints", params={"token_id": market.yes_token_id})
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("Polymarket CLOB /midpoints failed for %s: %s", market.external_id, exc)
            return None

        data = resp.json()
        # Response shape: {"mid": "0.73"} or {token_id: "0.73"}
        mid_raw = data.get("mid") or data.get(market.yes_token_id)
        if mid_raw is None:
            return None

        yes_price = float(mid_raw)
        return PolymarketSnapshot(
            external_id=market.external_id,
            yes_price=yes_price,
            no_price=1.0 - yes_price,
            volume_24h=None,
            timestamp=datetime.now(timezone.utc),
        )
