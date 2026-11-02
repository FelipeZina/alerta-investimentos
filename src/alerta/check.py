"""Verifica as cotações das posições e envia alertas no Telegram.

Uso:
    uv run python -m alerta.check             # execução real
    uv run python -m alerta.check --dry-run   # só mostra, não grava nem envia
"""

import argparse
import logging
import sys
from datetime import datetime

from alerta import db, rules
from alerta.brapi import BrapiClient, BrapiError
from alerta.config import get_settings
from alerta.models import B3_TZ
from alerta.telegram import TelegramClient, TelegramError

log = logging.getLogger("alerta.check")


def run(dry_run: bool = False, any_day: bool = False) -> int:
    """Retorna o número de falhas (0 = tudo certo)."""
    settings = get_settings()
    threshold = settings.alert_threshold_pct
    today = datetime.now(B3_TZ).date()
    failures = 0

    with (
        db.connect(settings.database_url) as conn,
        BrapiClient(settings.brapi_token) as brapi,
        TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id) as telegram,
    ):
        positions = db.get_positions(conn)
        if not positions:
            log.warning("Nenhuma posição cadastrada na tabela positions.")
            return 0

        for position in positions:
            try:
                quote = brapi.get_quote(position.ticker, today=today)
            except BrapiError as exc:
                log.error("%s", exc)
                failures += 1
                continue

            log.info(
                "%s: R$ %s (%s%%) pregão %s",
                quote.ticker,
                quote.price,
                quote.change_pct,
                quote.trade_date,
            )

            if quote.trade_date != today and not any_day:
                log.info("%s: sem pregão hoje, ignorando.", quote.ticker)
                continue

            if not dry_run and not db.save_quote(conn, quote):
                log.info("%s: preço igual à última leitura.", quote.ticker)

            signal = rules.classify(quote.change_pct, threshold)
            if signal is None:
                continue
            if not rules.should_alert(
                signal, db.get_max_alert_level(conn, quote, signal.direction)
            ):
                log.info("%s: nível %s já alertado.", quote.ticker, signal.level)
                continue

            message = rules.format_message(quote, signal, threshold, position)
            if dry_run:
                log.info("[dry-run] alerta que seria enviado:\n%s", message)
                continue

            try:
                telegram.send(message)
            except TelegramError as exc:
                log.error("%s: %s", quote.ticker, exc)
                failures += 1
                continue

            db.save_alert(conn, quote, signal.direction, signal.level)
            log.info("%s: alerta nível %s enviado.", quote.ticker, signal.level)

            # Grava a cada ação: se a próxima falhar, o que já foi feito não se perde.
            conn.commit()

        conn.commit()

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(description="Verifica cotações e envia alertas.")
    parser.add_argument("--dry-run", action="store_true", help="não grava nem envia nada")
    parser.add_argument(
        "--any-day", action="store_true", help="processa mesmo sem pregão hoje (para testes)"
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    # O httpx loga a URL de cada request, e a URL do Telegram contém o token do bot.
    logging.getLogger("httpx").setLevel(logging.WARNING)
    failures = run(dry_run=args.dry_run, any_day=args.any_day)
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
