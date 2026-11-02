from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
import pytest
import respx

from alerta.brapi import BASE_URL, BrapiClient, BrapiError, infer_trade_date

# Candles diários da brapi vêm marcados à meia-noite de Brasília (UTC-3).
OCT_28 = 1793156400
OCT_29 = 1793242800
OCT_30 = 1793329200
NOV_02 = 1793588400
TODAY = date(2026, 11, 2)


def candle(ts: int, close: float) -> dict:
    return {"date": ts, "close": close}


PETR4_PAYLOAD = {
    "results": [
        {
            "symbol": "PETR4",
            "regularMarketPrice": 52.71,
            "regularMarketChangePercent": 0.98,
            "regularMarketPreviousClose": 52.2,
            "regularMarketTime": "2026-11-02T15:50:30.000Z",
            "historicalDataPrice": [candle(OCT_29, 52.2), candle(OCT_30, 52.71)],
        }
    ]
}


@pytest.fixture
def client():
    with BrapiClient(token="token-de-teste") as c:
        yield c


@respx.mock
def test_get_quote_converte_resposta(client):
    route = respx.get(f"{BASE_URL}/quote/PETR4").mock(
        return_value=httpx.Response(200, json=PETR4_PAYLOAD)
    )

    quote = client.get_quote("PETR4", today=TODAY)

    assert quote.ticker == "PETR4"
    assert quote.price == Decimal("52.71")
    assert quote.change_pct == Decimal("0.98")
    assert quote.prev_close == Decimal("52.2")
    assert quote.market_time == datetime(2026, 11, 2, 15, 50, 30, tzinfo=UTC)
    assert quote.trade_date == date(2026, 10, 30)
    request = route.calls.last.request
    assert request.headers["Authorization"] == "Bearer token-de-teste"
    assert request.url.params["range"] == "5d"


@respx.mock
def test_ticker_inexistente_gera_brapi_error(client):
    respx.get(f"{BASE_URL}/quote/XXXX99").mock(
        return_value=httpx.Response(
            404, json={"error": True, "message": "Nenhum resultado encontrado"}
        )
    )

    with pytest.raises(BrapiError, match="404 - Nenhum resultado encontrado"):
        client.get_quote("XXXX99")


@respx.mock
def test_falha_de_rede_gera_brapi_error(client):
    respx.get(f"{BASE_URL}/quote/PETR4").mock(side_effect=httpx.ConnectTimeout("timeout"))

    with pytest.raises(BrapiError, match="falha de rede"):
        client.get_quote("PETR4")


@respx.mock
def test_resposta_sem_candles_gera_brapi_error(client):
    payload = {"results": [{**PETR4_PAYLOAD["results"][0], "historicalDataPrice": []}]}
    respx.get(f"{BASE_URL}/quote/PETR4").mock(return_value=httpx.Response(200, json=payload))

    with pytest.raises(BrapiError, match="resposta inesperada"):
        client.get_quote("PETR4")


def test_feriado_usa_data_do_ultimo_pregao():
    # 02/11 é feriado: a brapi ainda mostra a sexta (30/10) vs quinta (29/10)
    result = {
        "regularMarketPreviousClose": 71.77,
        "historicalDataPrice": [candle(OCT_28, 70), candle(OCT_29, 71.77), candle(OCT_30, 69.28)],
    }
    assert infer_trade_date(result, TODAY) == date(2026, 10, 30)


def test_pregao_em_andamento_com_candle_de_hoje():
    result = {
        "regularMarketPreviousClose": 69.28,
        "historicalDataPrice": [candle(OCT_29, 71.77), candle(OCT_30, 69.28), candle(NOV_02, 70.1)],
    }
    assert infer_trade_date(result, TODAY) == TODAY


def test_pregao_em_andamento_sem_candle_de_hoje():
    result = {
        "regularMarketPreviousClose": 69.28,
        "historicalDataPrice": [candle(OCT_29, 71.77), candle(OCT_30, 69.28)],
    }
    assert infer_trade_date(result, TODAY) == TODAY
