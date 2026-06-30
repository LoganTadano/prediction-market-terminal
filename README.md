# EdgeFinder v2

A Bloomberg Terminal for prediction markets. Unified price history, semantic cross-platform market matching, and an ML-powered edge leaderboard across Kalshi and Polymarket.

## What it does

Prediction markets on Kalshi and Polymarket list overlapping events under different titles. EdgeFinder ingests both platforms continuously, matches equivalent markets using sentence-transformer embeddings, and surfaces price discrepancies as tradeable edges.

**Core insight:** semantic market matching (embeddings, not string matching) unlocks a signal layer nobody else has built.

## Stack

| Layer | Tech |
|---|---|
| API | FastAPI + WebSockets |
| DB | PostgreSQL 15 + pgvector |
| Ingestion | httpx async clients + APScheduler |
| Matching | sentence-transformers (all-MiniLM-L6-v2) |
| Edge model | XGBoost + SHAP |
| Frontend | React (planned) |
| Infra | Docker + AWS EC2 |

## Project status

### Done

**Phase 0 — Data pipeline (June 2026)**

- Async ingestion clients for Kalshi () and Polymarket (Gamma API)
- PostgreSQL schema: , , , , 
-  extension wired up for future embedding storage
-  upserts — safe to re-run on every cycle
- APScheduler polling both platforms every 5 minutes via FastAPI lifespan
- Initial Alembic migration applied
- 18 unit tests + 1 live integration test, all passing
- Verified live: **44,800 Kalshi markets + 2,100 Polymarket markets** ingested on first run

### Next

| Phase | Target | Goal |
|---|---|---|
| 1 — History accumulation | Aug 2026 | 2+ months of price snapshots on disk |
| 2 — Market matching | Sep 2026 | Embed market titles, cosine-similarity pairs across platforms |
| 3 — Edge model | Oct 2026 | XGBoost trained on resolved cross-platform markets |
| 4 — Edge API | Nov 2026 | REST endpoint returning ranked edges with SHAP explanations |
| 5 — Dashboard | Jan 2027 | React UI: live prices, matched pairs, edge leaderboard |
| 6 — Accuracy tracking | Mar 2027 | Historical edge performance logged and surfaced |

## Quickstart

### Prerequisites

- Docker Desktop
- A Kalshi API key (from [kalshi.com](https://kalshi.com))

### Setup



Health check: {"status":"ok","environment":"development"}

### Run tests



## Environment variables

| Variable | Description |
|---|---|
|  | Postgres database name |
|  | Postgres user |
|  | Postgres password |
|  | Hostname ( inside Docker,  on host) |
|  | Postgres port (default 5432) |
|  | Kalshi API key UUID |
|  | Kalshi API secret (for future RSA-signed endpoints) |
|  |  or  |

## Repository layout

```
backend/
  ingestion/
    kalshi.py         # Kalshi async client + dataclasses
    polymarket.py     # Polymarket Gamma + CLOB clients
    store.py          # DB upsert helpers
    scheduler.py      # APScheduler job definitions
  migrations/
    versions/         # Alembic migration files
  tests/
    test_kalshi.py
    test_polymarket.py
    test_store.py
  config.py           # Pydantic settings (reads .env)
  database.py         # Async SQLAlchemy engine + session
  models.py           # ORM models (Market, PriceSnapshot, ...)
  main.py             # FastAPI app + lifespan
frontend/             # React dashboard (planned)
docker-compose.yml
```
