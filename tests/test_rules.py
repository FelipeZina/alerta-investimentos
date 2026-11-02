from decimal import Decimal

import pytest

from alerta.models import Position
from alerta.rules import Signal, classify, fmt_brl, format_message, should_alert
from tests.factories import make_quote

D = Decimal
THRESHOLD = D("3")


@pytest.mark.parametrize(
    ("change_pct", "expected"),
    [
        ("0", None),
        ("2.99", None),
        ("-2.99", None),
        ("3", Signal("up", 1)),
        ("-3", Signal("down", 1)),
        ("-4.2", Signal("down", 1)),
        ("5.99", Signal("up", 1)),
        ("6", Signal("up", 2)),
        ("-10.5", Signal("down", 3)),
    ],
)
def test_classify(change_pct, expected):
    assert classify(D(change_pct), THRESHOLD) == expected


def test_classify_rejeita_threshold_invalido():
    with pytest.raises(ValueError):
        classify(D("5"), D("0"))


@pytest.mark.parametrize(
    ("level", "max_sent", "expected"),
    [(1, 0, True), (1, 1, False), (2, 1, True), (1, 2, False)],
)
def test_should_alert(level, max_sent, expected):
    assert should_alert(Signal("down", level), max_sent) is expected


def test_fmt_brl_padrao_brasileiro():
    assert fmt_brl(D("1234.5")) == "R$ 1.234,50"
    assert fmt_brl(D("-720"), sign=True) == "-R$ 720,00"


def test_mensagem_sem_posicao():
    msg = format_message(make_quote("-4.2"), Signal("down", 1), THRESHOLD)
    assert msg == (
        "🔻 <b>ITUB4</b> caiu 4,20% hoje (passou de 3%)\nPreço: R$ 36,10 | fech. ant. R$ 37,68"
    )


def test_mensagem_com_posicao_mostra_resultado():
    position = Position(ticker="ITUB4", quantity=100, avg_price=D("28.90"))
    msg = format_message(make_quote("-4.2"), Signal("down", 1), THRESHOLD, position)
    assert msg.splitlines()[-1] == ("Sua posição: 100 cotas · PM R$ 28,90 · +24,91% (+R$ 720,00)")


def test_mensagem_nivel_2_alta():
    msg = format_message(make_quote("6.5", price="40.13"), Signal("up", 2), THRESHOLD)
    assert msg.startswith("🔺 <b>ITUB4</b> subiu 6,50% hoje (passou de 6%)")


def test_mensagem_limite_fracionado_nao_arredonda():
    msg = format_message(make_quote("-0.65"), Signal("down", 1), D("0.5"))
    assert "(passou de 0,50%)" in msg
