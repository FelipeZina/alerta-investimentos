"""Acesso ao banco Postgres."""

from decimal import Decimal

import psycopg
from psycopg.rows import class_row
from pydantic import BaseModel


class Position(BaseModel):
    ticker: str
    quantity: int
    avg_price: Decimal


def connect(database_url: str) -> psycopg.Connection:
    return psycopg.connect(database_url)


def get_positions(conn: psycopg.Connection) -> list[Position]:
    with conn.cursor(row_factory=class_row(Position)) as cur:
        cur.execute("SELECT ticker, quantity, avg_price FROM positions ORDER BY ticker")
        return cur.fetchall()
