import json

import httpx
import pytest
import respx

from alerta.telegram import TelegramClient, TelegramError

URL = "https://api.telegram.org/botTOKEN/sendMessage"


@pytest.fixture
def client():
    with TelegramClient(bot_token="TOKEN", chat_id="123") as c:
        yield c


@respx.mock
def test_send_envia_chat_id_texto_e_html(client):
    route = respx.post(URL).mock(return_value=httpx.Response(200, json={"ok": True}))

    client.send("<b>oi</b>")

    body = json.loads(route.calls.last.request.content)
    assert body == {"chat_id": "123", "text": "<b>oi</b>", "parse_mode": "HTML"}


@respx.mock
def test_send_recusado_gera_telegram_error(client):
    respx.post(URL).mock(
        return_value=httpx.Response(
            400, json={"ok": False, "description": "Bad Request: chat not found"}
        )
    )

    with pytest.raises(TelegramError, match="chat not found"):
        client.send("oi")


@respx.mock
def test_erro_de_rede_nao_vaza_token(client):
    respx.post(URL).mock(side_effect=httpx.ConnectError("falhou em .../botTOKEN/..."))

    with pytest.raises(TelegramError) as exc_info:
        client.send("oi")
    assert "TOKEN" not in str(exc_info.value)
