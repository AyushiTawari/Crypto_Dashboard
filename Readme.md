# Live Crypto Dashboard

A real-time cryptocurrency market dashboard built to practice production-style
service architecture: a live Binance websocket feed, Redis as a decoupling
layer, a FastAPI backend serving both live data and REST endpoints, and a
Streamlit + JS frontend with live-updating charts, KPIs, and a searchable
symbol table.

## What it does

- Streams live trade data for 8 crypto symbols (BTC, ETH, SOL, BNB, XRP, ADA,
  DOGE, DOT) directly from Binance's public websocket
- Computes rolling 60-second features per symbol (VWAP, price change %,
  trade count, volume) in-memory
- Serves live data over both REST and websocket endpoints via FastAPI
- Renders a live dashboard: KPI cards (highest price, lowest price, most
  traded), a live area chart for the most-traded symbol, and a searchable
  table of all tracked symbols with live sparklines
- Pulls 24h high/low from Binance's own ticker endpoint (cached, since
  crypto has no market close and this is a rolling window, not a
  calendar-day boundary)
- Fully containerized with Docker Compose (Redis, ingestion, API, dashboard
  as separate services)

## Architecture

Binance websocket
|
v
Ingestion service (async consumer, rolling feature engineering)
|
v
Redis (pub/sub + latest-snapshot cache)
|
v
FastAPI backend (REST + websocket + Binance 24h proxy)
|
v
Streamlit + JS dashboard (live charts, KPIs, searchable table)

Each stage is an independent process, communicating only through Redis or
HTTP/websocket — not direct function calls. The ingestion service can
restart without the API losing its last-known state, and vice versa. This
is also why scaling from 2 tracked symbols to 8 required a one-line config
change (`SYMBOLS` in `.env`) and no code changes at all — the abstraction
boundaries were drawn around "one symbol's data," not "the two symbols we
started with."

## Tech stack

| Layer            | Tool                                      |
|-------------------|--------------------------------------------|
| Ingestion         | `asyncio`, `websockets`                    |
| Cache / message bus | Redis (pub/sub + key-value)              |
| API               | FastAPI, Pydantic                          |
| Frontend          | Streamlit, embedded HTML/JS, Plotly.js     |
| Config            | `pydantic-settings`, `.env`                |
| Logging           | loguru (file + console, rotating)          |
| Containerization  | Docker, Docker Compose                     |

## Project layout

config/ Centralised settings (pydantic-settings, reads .env)
ingestion/ Binance websocket client, feature engine, Redis client
app/ FastAPI backend (routers, snapshot + websocket + 24h ticker)
dashboard/ Streamlit app with embedded JS for live charts/tables
scripts/ Throwaway smoke-test scripts used during development
logs/ Rotating log files (gitignored)


## Why a JS-embedded frontend, not pure Streamlit

Streamlit's default model reruns the entire script on every update, which
causes visible flicker and lost scroll position for anything updating more
than once every few seconds. Live prices need to update far more often than
that to feel real. The dashboard instead embeds raw HTML/JS via
`streamlit.components.v1.html`, opens its own native browser `WebSocket`
connection to FastAPI, and updates chart/table elements in place with
Plotly.js — Streamlit renders the page once and gets out of the way after
that.

## Setup

```bash
python3 -m venv venv
venv\Scripts\activate

pip install -r requirements.txt   

cp .env.example .env
```

### Running locally (without Docker)

Each service runs in its own terminal:

```bash
# Redis (if not already running)
docker run --name crypto-redis -p 6379:6379 -d redis:7

# Ingestion — streams live trades into Redis
python -m ingestion.main

# API — serves REST + websocket endpoints
uvicorn app.main:app --reload --port 8000

# Dashboard
streamlit run dashboard/app.py
```

Dashboard: http://localhost:8501
API docs: http://localhost:8000/docs

### Running with Docker Compose

```bash
docker compose up --build
```

Starts Redis, ingestion, the API, and the dashboard together.

```bash
docker compose down
```
