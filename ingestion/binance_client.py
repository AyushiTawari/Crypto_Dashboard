import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
import websockets

@dataclass
class Trade:
    symbol: str
    price: float
    quantity: float
    timestamp_ms: int
    is_buyer_maker: bool

def _build_stream_url(base_url: str, symbols: list[str]) -> str:
    streams = "/".join(f"{s}@trade" for s in symbols)
    return f"{base_url.rstrip('/ws')}/stream?streams={streams}"

def _parse_trade(raw: dict) -> Trade:
    payload = raw["data"]
    return Trade(
        symbol=payload["s"].lower(),
        price=float(payload["p"]),
        quantity=float(payload["q"]),
        timestamp_ms=payload["T"],
        is_buyer_maker=payload["m"],
    )

async def stream_trades(base_url: str, symbols: list[str]) -> AsyncIterator[Trade]:
    url = _build_stream_url(base_url, symbols)
    retry_delay = 1
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                retry_delay = 1
                async for raw_message in ws:
                    data = json.loads(raw_message)
                    yield _parse_trade(data)
        except (websockets.ConnectionClosed, OSError):
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60)