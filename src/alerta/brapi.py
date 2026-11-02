"""Cliente da API brapi.dev."""

import sys
from datetime import datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel, Field

BASE_URL = "https://brapi.dev/api"


class Quote(BaseModel):
    ticker: str = Field(alias="symbol")
    price: Decimal = Field(alias="regularMarketPrice")
    change_pct: Decimal = Field(alias="regularMarketChangePercent")
    prev_close: Decimal = Field(alias="regularMarketPreviousClose")
    market_time: datetime = Field(alias="regularMarketTime")


class BrapiError(Exception):
    pass


class BrapiClient:
    def __init__(self, token: str, timeout: float = 15.0) -> None:
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            transport=httpx.HTTPTransport(retries=2),
        )

    def get_quote(self, ticker: str) -> Quote:
        try:
            response = self._http.get(f"/quote/{ticker}")
        except httpx.HTTPError as exc:
            raise BrapiError(f"{ticker}: falha de rede ({exc})") from exc

        if response.is_error:
            message = response.json().get("message", response.text) if response.content else ""
            raise BrapiError(f"{ticker}: HTTP {response.status_code} - {message}")

        results = response.json().get("results") or []
        if not results:
            raise BrapiError(f"{ticker}: resposta sem resultados")
        return Quote.model_validate(results[0])

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BrapiClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


if __name__ == "__main__":
    from alerta import db
    from alerta.config import get_settings

    settings = get_settings()
    tickers = sys.argv[1:]
    if not tickers:
        with db.connect(settings.database_url) as conn:
            tickers = [p.ticker for p in db.get_positions(conn)]

    with BrapiClient(settings.brapi_token) as client:
        for t in tickers:
            try:
                print(client.get_quote(t))
            except BrapiError as e:
                print(f"ERRO: {e}")
