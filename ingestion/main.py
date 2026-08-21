import asyncio
from loguru import logger
from ingestion.binance_client import stream_trades
from ingestion.features import FeatureEngine
from ingestion.redis_client import SnapshotStore
from config.settings import get_settings

logger.add("logs/ingestion.log", rotation="10 MB", retention="7 days")
async def run() -> None:
    settings = get_settings()
    engine = FeatureEngine(window_seconds=60)
    store = SnapshotStore(settings.redis_host, settings.redis_port)

    logger.info(f"Starting ingestion for symbols: {settings.symbol_list}")

    async for trade in stream_trades(settings.binance_ws_url, settings.symbol_list):
        snapshot = engine.process(trade)
        store.save(snapshot)
        print(snapshot)

if __name__ == "__main__":
    asyncio.run(run())