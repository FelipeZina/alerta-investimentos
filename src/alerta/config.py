"""Configuração do app, lida de variáveis de ambiente (ou do arquivo .env).

Localmente os valores vêm do .env; no GitHub Actions, dos secrets do repositório.
O pydantic-settings valida os tipos: se ALERT_THRESHOLD_PCT vier "abc", o app
falha logo no início com uma mensagem clara, em vez de quebrar no meio.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    brapi_token: str
    telegram_bot_token: str
    telegram_chat_id: str
    database_url: str

    tickers: str
    alert_threshold_pct: float = 3.0

    @property
    def ticker_list(self) -> list[str]:
        return [t.strip().upper() for t in self.tickers.split(",") if t.strip()]


@lru_cache
def get_settings() -> Settings:
    """Cria o Settings uma única vez e reaproveita nas próximas chamadas."""
    return Settings()
