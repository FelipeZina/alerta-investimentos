"""Tipos compartilhados entre os módulos."""

from decimal import Decimal
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

B3_TZ = ZoneInfo("America/Sao_Paulo")

Direction = Literal["up", "down"]


class Position(BaseModel):
    ticker: str
    quantity: int
    avg_price: Decimal
