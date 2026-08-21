from fastapi import APIRouter, HTTPException
from ingestion.redis_client import SnapshotStore
from config.settings import get_settings
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import httpx

router = APIRouter()
settings = get_settings()
store = SnapshotStore(settings.redis_host, settings.redis_port)

@router.get("/snapshots/{symbol}")
def get_snapshot(symbol: str):
    data = store.get(symbol)
    if data is None:
        raise HTTPException(status_code=404, detail=f"No snapshot found for {symbol}")
    return data

@router.websocket("/ws/{symbol}")
async def websocket_snapshot(websocket: WebSocket, symbol: str):
    await websocket.accept()
    pubsub = store.subscribe(symbol)
    try:
        while True:
            message = pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if message:
                await websocket.send_text(message["data"])
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        pubsub.close()

@router.get("/snapshots")
def list_snapshots():
    settings = get_settings()
    results = []
    for symbol in settings.symbol_list:
        data = store.get(symbol)
        if data:
            results.append(data)
    return results

@router.websocket("/ws")
async def websocket_all_snapshots(websocket: WebSocket):
    await websocket.accept()
    settings = get_settings()
    pubsubs = {symbol: store.subscribe(symbol) for symbol in settings.symbol_list}
    try:
        while True:
            for symbol, pubsub in pubsubs.items():
                message = pubsub.get_message(ignore_subscribe_messages=True, timeout=0.01)
                if message:
                    await websocket.send_text(message["data"])
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        for pubsub in pubsubs.values():
            pubsub.close()

@router.get("/ticker24h/{symbol}")
def get_ticker_24h(symbol: str):
    url = f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol.upper()}"
    response = httpx.get(url, timeout=5.0)
    if response.status_code != 200:
        raise HTTPException(status_code=502, detail="Failed to fetch 24hr ticker from Binance")
    data = response.json()
    return {
        "symbol": symbol.lower(),
        "high_price": float(data["highPrice"]),
        "low_price": float(data["lowPrice"]),
    }