"""Regras de alerta. Funções puras: não acessam rede nem banco."""

from dataclasses import dataclass
from decimal import Decimal

from alerta.brapi import Quote
from alerta.models import Direction, Position


@dataclass(frozen=True)
class Signal:
    direction: Direction
    level: int


def classify(change_pct: Decimal, threshold: Decimal) -> Signal | None:
    """Ex.: threshold 3 -> -4% = ('down', 1), +7% = ('up', 2), 2% = None."""
    if threshold <= 0:
        raise ValueError("threshold deve ser maior que zero")
    level = int(abs(change_pct) // threshold)
    if level == 0:
        return None
    return Signal("up" if change_pct > 0 else "down", level)


def should_alert(signal: Signal, max_level_sent: int) -> bool:
    return signal.level > max_level_sent


def format_message(
    quote: Quote, signal: Signal, threshold: Decimal, position: Position | None = None
) -> str:
    emoji, verb = ("🔺", "subiu") if signal.direction == "up" else ("🔻", "caiu")
    limit = threshold * signal.level
    limit_decimals = 0 if limit == limit.to_integral_value() else 2
    lines = [
        f"{emoji} <b>{quote.ticker}</b> {verb} {fmt_pct(abs(quote.change_pct))} hoje "
        f"(passou de {fmt_pct(limit, decimals=limit_decimals)})",
        f"Preço: {fmt_brl(quote.price)} | fech. ant. {fmt_brl(quote.prev_close)}",
    ]
    if position:
        pnl = (quote.price - position.avg_price) * position.quantity
        pnl_pct = (quote.price / position.avg_price - 1) * 100
        lines.append(
            f"Sua posição: {position.quantity} cotas · PM {fmt_brl(position.avg_price)} · "
            f"{fmt_pct(pnl_pct, sign=True)} ({fmt_brl(pnl, sign=True)})"
        )
    return "\n".join(lines)


def _br_number(value: Decimal, decimals: int) -> str:
    """1234.5 -> '1.234,50' (padrão brasileiro)."""
    us = f"{value:,.{decimals}f}"
    return us.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_brl(value: Decimal, sign: bool = False) -> str:
    prefix = ("+" if value >= 0 else "-") if sign else ("-" if value < 0 else "")
    return f"{prefix}R$ {_br_number(abs(value), 2)}"


def fmt_pct(value: Decimal, decimals: int = 2, sign: bool = False) -> str:
    prefix = ("+" if value >= 0 else "-") if sign else ("-" if value < 0 else "")
    return f"{prefix}{_br_number(abs(value), decimals)}%"
