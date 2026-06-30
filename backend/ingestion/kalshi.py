"""
Kalshi ingestion client.

Docs: https://trading-api.kalshi.com/trade-api/v2/
Auth: RSA-signed requests (PKCS1v15 + SHA-256). Each request is signed with
      your private key so Kalshi can verify it came from you. The signature
      covers (timestamp_ms + METHOD + path), which also prevents replay attacks.

      Required env vars:
        KALSHI_API_KEY     — your key UUID from the Kalshi dashboard
        KALSHI_API_SECRET  — PEM contents of your RSA private key (with real newlines)
"""

import base64
import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

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


class KalshiAuth(httpx.Auth):
    """
    Per-request RSA signer for the Kalshi v2 trading API.

    httpx calls auth_flow() before each request so we can stamp a fresh
    timestamp and path-specific signature onto the headers.

    Kalshi verifies three headers:
      Kalshi-Access-Key        — identifies which public key to check against
      Kalshi-Access-Timestamp  — milliseconds since epoch (prevents replay)
      Kalshi-Access-Signature  — base64(RSA_SHA256(timestamp + METHOD + path))
    """

    def __init__(self, api_key: str, private_key_path: str):
        self.api_key = api_key
        with open(private_key_path, "rb") as f:
            self._private_key = serialization.load_pem_private_key(f.read(), password=None)

    def auth_flow(self, request: httpx.Request):
        timestamp_ms = int(time.time() * 1000)
        message = str(timestamp_ms) + request.method + request.url.raw_path.decode()
        signature_bytes = self._private_key.sign(
            message.encode("utf-8"), padding.PKCS1v15(), hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature_bytes).decode("utf-8")

        request.headers["Kalshi-Access-Key"] = self.api_key
        request.headers["Kalshi-Access-Timestamp"] = str(timestamp_ms)
        request.headers["Kalshi-Access-Signature"] = signature_b64

        yield request


def _build_client() -> httpx.AsyncClient:
    auth = None
    if settings.kalshi_api_key and settings.kalshi_private_key_path:
        auth = KalshiAuth(settings.kalshi_api_key, settings.kalshi_private_key_path)
    return httpx.AsyncClient(
        base_url=BASE_URL,
        headers={"Accept": "application/json"},
        auth=auth,
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
