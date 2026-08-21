import json
import redis
from dataclasses import asdict
from ingestion.features import FeatureSnapshot

class SnapshotStore:
    def __init__(self, host: str, port: int):
        self.client = redis.Redis(host=host, port=port, decode_responses=True)

    def save(self, snapshot: FeatureSnapshot) -> None:
        key = f"snapshot:{snapshot.symbol}"
        value = json.dumps(asdict(snapshot))
        self.client.set(key, value)
        self.client.publish(f"channel:{snapshot.symbol}", value)

    def get(self, symbol: str) -> dict | None:
        value = self.client.get(f"snapshot:{symbol}")
        if value is None:
            return None
        return json.loads(value)

    def subscribe(self, symbol: str):
        pubsub = self.client.pubsub()
        pubsub.subscribe(f"channel:{symbol}")
        return pubsub