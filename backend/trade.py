from dataclasses import dataclass
from typing import Literal

@dataclass
class TradeOffer:
    id: str
    type: Literal["sell", "buy"]
    from_player: int
    to_player: int
    cell_id: int
    price: int
