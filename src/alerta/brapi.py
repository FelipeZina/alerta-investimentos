"""Cliente da API brapi.dev."""

import sys
from datetime import date, datetime
from decimal import Decimal

import httpx
from pydantic import BaseModel, Field

from alerta.models import B3_TZ

BASE_URL = "https://brapi.dev/api"


class Quote(BaseModel):
    ticker: str = Field(alias="symbol")
    price: Decimal = Field(alias="regularMarketPrice")
    change_pct: Decimal = Field(alias="regularMarketChangePercent")
    prev_close: Decimal = Field(alias="regularMarketPreviousClose")
    market_time: datetime = Field(alias="regularMarketTime")
    trade_date: date


class BrapiError(Exception):
    pass


def infer_trade_date(result: dict, today: date) -> date:
    """Descobre a data do pregão a que a cotação se refere.

    O regularMarketTime da brapi é o horário de atualização do dado, não do
    pregão. Usamos os candles diários (range=5d):
    - penúltimo candle fechou no prev_close -> o último candle é o pregão atual;
    - último candle fechou no prev_close -> o candle de hoje ainda não existe,
      então a cotação é de hoje.
    """
    candles = result.get("historicalDataPrice") or []
    if not candles:
        raise ValueError("resposta sem historicalDataPrice")

    prev_close = Decimal(str(result["regularMarketPreviousClose"]))
    last = candles[-1]
    last_date = datetime.fromtimestamp(last["date"], B3_TZ).date()

    if len(candles) >= 2 and Decimal(str(candles[-2]["close"])) == prev_close:
        return last_date
    if Decimal(str(last["close"])) == prev_close and last_date < today:
        return today
    return last_date


class BrapiClient:
    def __init__(self, token: str, timeout: float = 15.0) -> None:
        self._http = httpx.Client(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=timeout,
            transport=httpx.HTTPTransport(retries=2),
        )

    def get_quote(self, ticker: str, today: date | None = None) -> Quote:
        today = today or datetime.now(B3_TZ).date()
        try:
            response = self._http.get(f"/quote/{ticker}", params={"range": "5d", "interval": "1d"})
        except httpx.HTTPError as exc:
            raise BrapiError(f"{ticker}: falha de rede ({exc})") from exc

        if response.is_error:
            message = response.json().get("message", response.text) if response.content else ""
            raise BrapiError(f"{ticker}: HTTP {response.status_code} - {message}")

        results = response.json().get("results") or []
        if not results:
            raise BrapiError(f"{ticker}: resposta sem resultados")

        result = results[0]
        try:
            return Quote.model_validate({**result, "trade_date": infer_trade_date(result, today)})
        except (ValueError, KeyError) as exc:
            raise BrapiError(f"{ticker}: resposta inesperada ({exc})") from exc

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
