"""Testes de integração: rodam contra um Postgres de verdade.

Só executam se TEST_DATABASE_URL estiver definido; senão são pulados.
Cada teste roda numa transação desfeita no final (rollback), então nada fica no banco.
"""

import os
from datetime import date

import psycopg
import pytest

from alerta import db
from tests.factories import make_quote


@pytest.fixture
def conn():
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL não definido")
    with psycopg.connect(url) as c:
        yield c
        c.rollback()


def test_save_quote_ignora_preco_repetido_no_mesmo_pregao(conn):
    assert db.save_quote(conn, make_quote(ticker="TEST3")) is True
    assert db.save_quote(conn, make_quote(ticker="TEST3")) is False
    assert db.save_quote(conn, make_quote(ticker="TEST3", price="36.20")) is True
    assert db.save_quote(conn, make_quote(ticker="TEST3", trade_date=date(2026, 11, 3))) is True


def test_max_alert_level_comeca_em_zero(conn):
    assert db.get_max_alert_level(conn, make_quote(ticker="TEST3"), "down") == 0


def test_max_alert_level_considera_ticker_pregao_e_direcao(conn):
    quote = make_quote(ticker="TEST3")
    db.save_alert(conn, quote, "down", 1)
    db.save_alert(conn, quote, "down", 2)
    db.save_alert(conn, quote, "down", 2)  # repetido: ignorado

    assert db.get_max_alert_level(conn, quote, "down") == 2
    assert db.get_max_alert_level(conn, quote, "up") == 0
    next_day = make_quote(ticker="TEST3", trade_date=date(2026, 11, 3))
    assert db.get_max_alert_level(conn, next_day, "down") == 0
