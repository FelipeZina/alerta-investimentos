"""Acesso ao banco Postgres."""

import psycopg
from psycopg.rows import class_row

from alerta.brapi import Quote
from alerta.models import Direction, Position


def connect(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def get_positions(conn: psycopg.Connection) -> list[Position]:
    with conn.cursor(row_factory=class_row(Position)) as cur:
        cur.execute("SELECT ticker, quantity, avg_price FROM positions ORDER BY ticker")
        return cur.fetchall()


def save_quote(conn: psycopg.Connection, quote: Quote) -> bool:
    """Grava a cotação. Retorna False se o mesmo preço já foi gravado para esse pregão."""
    row = conn.execute(
        """
        INSERT INTO quotes (ticker, price, change_pct, prev_close, market_time, trade_date)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, trade_date, price) DO NOTHING
        RETURNING id
        """,
        (
            quote.ticker,
            quote.price,
            quote.change_pct,
            quote.prev_close,
            quote.market_time,
            quote.trade_date,
        ),
    ).fetchone()
    return row is not None


def get_max_alert_level(conn: psycopg.Connection, quote: Quote, direction: Direction) -> int:
    row = conn.execute(
        """
        SELECT COALESCE(MAX(level), 0)
        FROM alerts
        WHERE ticker = %s AND trade_date = %s AND direction = %s
        """,
        (quote.ticker, quote.trade_date, direction),
    ).fetchone()
    return row[0]


def save_alert(conn: psycopg.Connection, quote: Quote, direction: Direction, level: int) -> None:
    conn.execute(
        """
        INSERT INTO alerts (ticker, trade_date, direction, level, change_pct, price)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (ticker, trade_date, direction, level) DO NOTHING
        """,
        (quote.ticker, quote.trade_date, direction, level, quote.change_pct, quote.price),
    )
