from datetime import UTC, date, datetime
from decimal import Decimal

from alerta.brapi import Quote


def make_quote(
    change_pct: str = "-4.2",
    price: str = "36.10",
    prev_close: str = "37.68",
    ticker: str = "ITUB4",
    trade_date: date = date(2026, 11, 2),
) -> Quote:
    return Quote(
        symbol=ticker,
        regularMarketPrice=Decimal(price),
        regularMarketChangePercent=Decimal(change_pct),
        regularMarketPreviousClose=Decimal(prev_close),
        regularMarketTime=datetime(2026, 11, 2, 15, 0, tzinfo=UTC),
        trade_date=trade_date,
    )
