import asyncio
from ingestion.binance_client import stream_trades
from ingestion.features import FeatureEngine
from ingestion.redis_client import SnapshotStore
from config.settings import get_settings


async def main():
    settings = get_settings()
    engine = FeatureEngine(window_seconds=60)
    store = SnapshotStore(settings.redis_host, settings.redis_port)
    count = 0
    async for trade in stream_trades(settings.binance_ws_url, settings.symbol_list):
        snapshot = engine.process(trade)
        store.save(snapshot)
        print(store.get(snapshot.symbol))
        count += 1
        if count >= 10:
            break


asyncio.run(main())