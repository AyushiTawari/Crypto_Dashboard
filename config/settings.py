from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    environment: str = "development"
    log_level: str = "INFO"

    binance_ws_url: str = "wss://stream.binance.com:9443/ws"
    symbols: str = "btcusdt,ethusdt"

    redis_host: str = "localhost"
    redis_port: int = 6379

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )
    @property
    def symbol_list(self) -> list[str]:
        return [s.strip().lower() for s in self.symbols.split(",") if s.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()