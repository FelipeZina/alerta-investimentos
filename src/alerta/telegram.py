"""Envio de mensagens pelo bot do Telegram."""

import httpx


class TelegramError(Exception):
    pass


class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str, timeout: float = 15.0) -> None:
        self._chat_id = chat_id
        self._http = httpx.Client(
            base_url=f"https://api.telegram.org/bot{bot_token}",
            timeout=timeout,
            transport=httpx.HTTPTransport(retries=2),
        )

    def send(self, text: str) -> None:
        try:
            response = self._http.post(
                "/sendMessage",
                json={"chat_id": self._chat_id, "text": text, "parse_mode": "HTML"},
            )
        except httpx.HTTPError as exc:
            raise TelegramError(f"falha de rede ao enviar mensagem ({type(exc).__name__})") from exc

        data = response.json()
        if not data.get("ok"):
            raise TelegramError(f"Telegram recusou a mensagem: {data.get('description')}")

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "TelegramClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
