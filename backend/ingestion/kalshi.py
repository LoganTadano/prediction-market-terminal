"""
Kalshi ingestion client.

Docs: https://trading-api.kalshi.com/trade-api/v2/
Auth: The v2 API uses RSA-signed requests. For read-only endpoints a plain
      Bearer header works in some environments; production requires HMAC signing.
      See config.py — kalshi_api_key and kalshi_api_secret are both wired up.
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx

from config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://api.elections.kalshi.com/trade-api/v2"
# BASE_URL = "https://demo-api.kalshi.co/trade-api/v2"


def _parse_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


@dataclass
class KalshiMarket:
    external_id: str       # Kalshi's ticker, e.g. "INXD-23DEC31-B4400"
    title: str
    category: str | None
    close_time: datetime | None
    resolved: bool
    resolution: str | None
    # Prices come from the list endpoint — no extra per-market call needed
    yes_price: float | None   # 0-1
    no_price: float | None
    volume_24h: float | None


@dataclass
class KalshiSnapshot:
    external_id: str
    yes_price: float
    no_price: float
    volume_24h: float | None
    timestamp: datetime


def _build_client() -> httpx.AsyncClient:
    headers = {"Accept": "application/json"}
    if settings.kalshi_api_key:
        headers["Authorization"] = f"Bearer {settings.kalshi_api_key}"
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers=headers,
        timeout=httpx.Timeout(10.0, connect=5.0),
    )


async def fetch_active_markets() -> list[KalshiMarket]:
    """
    Fetch all open Kalshi markets with cursor-based pagination.

    Prices (last_price, volume_24h) are included in the list response,
    so no separate per-market price call is needed in the hot path.
    """
    markets: list[KalshiMarket] = []
    cursor: str | None = None

    async with _build_client() as client:
        while True:
            params: dict = {"status": "open", "limit": 200}
            if cursor:
                params["cursor"] = cursor

            try:
                resp = await client.get("/markets", params=params)
                resp.raise_for_status()
            except httpx.HTTPStatusError as exc:
                logger.error("Kalshi GET /markets failed: %s", exc)
                break

            data = resp.json()
            page: list = data.get("markets", [])

            for m in page:
                # New API: prices are in last_price_dollars (0-1 range); volume is volume_24h_fp
                last_price_dollars = m.get("last_price_dollars")
                yes_price = float(last_price_dollars) if last_price_dollars is not None else None
                no_price = (1.0 - yes_price) if yes_price is not None else None
                vol = m.get("volume_24h_fp") or m.get("volume_fp")

                result = m.get("result", "")
                markets.append(KalshiMarket(
                    external_id=m["ticker"],
                    title=m.get("title", ""),
                    category=m.get("category"),
                    close_time=_parse_iso(m.get("close_time")),
                    resolved=(m.get("status") not in ("active", "open")),
                    resolution=result if result else None,
                    yes_price=yes_price,
                    no_price=no_price,
                    volume_24h=float(vol) if vol is not None else None,
                ))

            cursor = data.get("cursor") or None
            if not cursor or not page:
                break

    logger.info("Kalshi: fetched %d active markets", len(markets))
    return markets


async def fetch_market_price(ticker: str) -> KalshiSnapshot | None:
    """
    Fetch a fresh price for a single Kalshi market.

    Use this for on-demand refresh; the bulk path uses prices from
    fetch_active_markets instead.
    """
    async with _build_client() as client:
        try:
            resp = await client.get(f"/markets/{ticker}")
            resp.raise_for_status()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            logger.error("Kalshi GET /markets/%s failed: %s", ticker, exc)
            return None

        m = resp.json().get("market", {})
        last_price_dollars = m.get("last_price_dollars") or 0
        yes_price = float(last_price_dollars)
        no_price = 1.0 - yes_price
        vol = m.get("volume_24h_fp") or m.get("volume_fp")

        return KalshiSnapshot(
            external_id=ticker,
            yes_price=yes_price,
            no_price=no_price,
            volume_24h=float(vol) if vol is not None else None,
            timestamp=datetime.now(timezone.utc),
        )
