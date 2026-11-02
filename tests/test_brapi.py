from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest
import respx

from alerta.brapi import BASE_URL, BrapiClient, BrapiError

PETR4_PAYLOAD = {
    "results": [
        {
            "symbol": "PETR4",
            "regularMarketPrice": 52.71,
            "regularMarketChangePercent": 0.98,
            "regularMarketPreviousClose": 52.2,
            "regularMarketTime": "2026-11-02T15:50:30.000Z",
            "longName": "Petroleo Brasileiro SA Pfd",
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

    quote = client.get_quote("PETR4")

    assert quote.ticker == "PETR4"
    assert quote.price == Decimal("52.71")
    assert quote.change_pct == Decimal("0.98")
    assert quote.prev_close == Decimal("52.2")
    assert quote.market_time == datetime(2026, 11, 2, 15, 50, 30, tzinfo=UTC)
    assert route.calls.last.request.headers["Authorization"] == "Bearer token-de-teste"


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
