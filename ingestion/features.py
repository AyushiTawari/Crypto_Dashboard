import time
from collections import deque
from dataclasses import dataclass
from ingestion.binance_client import Trade

@dataclass
class FeatureSnapshot:
    symbol: str
    last_price: float
    vwap: float
    price_change_pct: float
    trade_count: int
    volume: float
    timestamp_ms: int

def compute_vwap(prices: list[float], volumes: list[float]) -> float:
    total_volume = sum(volumes)
    weighted_sum = sum(p * v for p, v in zip(prices, volumes))
    return weighted_sum / total_volume

def compute_price_change_pct(first_price: float, last_price: float) -> float:
    return ((last_price - first_price) / first_price) * 100

def build_snapshot(trades: list[Trade]) -> FeatureSnapshot:
    prices = [t.price for t in trades]
    volumes = [t.quantity for t in trades]
    return FeatureSnapshot(
        symbol=trades[0].symbol,
        last_price=prices[-1],
        vwap=round(compute_vwap(prices, volumes), 4),
        price_change_pct=round(compute_price_change_pct(prices[0], prices[-1]), 4),
        trade_count=len(trades),
        volume=round(sum(volumes), 6),
        timestamp_ms=trades[-1].timestamp_ms,
    )

class RollingWindow:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.trades: deque[Trade] = deque()

    def add(self, trade: Trade) -> None:
        self.trades.append(trade)
        self._evict_old(trade.timestamp_ms)

    def _evict_old(self, now_ms: int) -> None:
        cutoff = now_ms - self.window_seconds * 1000
        while self.trades and self.trades[0].timestamp_ms < cutoff:
            self.trades.popleft()

    def snapshot(self) -> FeatureSnapshot | None:
        if not self.trades:
            return None
        return build_snapshot(list(self.trades))

class FeatureEngine:
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self.windows: dict[str, RollingWindow] = {}

    def process(self, trade: Trade) -> FeatureSnapshot:
        if trade.symbol not in self.windows:
            self.windows[trade.symbol] = RollingWindow(self.window_seconds)
        window = self.windows[trade.symbol]
        window.add(trade)
        return window.snapshot()