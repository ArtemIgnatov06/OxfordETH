from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any, List

from .player import Player

# -------- Cells --------

class Cell:
    def __init__(self, cell_id: int, title: str):
        self.id = cell_id
        self.title = title

    def on_land(self, game: "Game", player: Player) -> Dict[str, Any]:
        return {"type": "noop", "cellId": self.id, "title": self.title}


class StartCell(Cell):
    def on_land(self, game: "Game", player: Player) -> Dict[str, Any]:
        return {"type": "start", "cellId": self.id, "title": self.title}


class NewsCell(Cell):
    def on_land(self, game: "Game", player: Player) -> Dict[str, Any]:
        # delegate to chance/news deck
        result = game.chance.apply(player)
        game.log(f"{player.name}: {result['text']} ({result['delta']} FC)")
        result.update({"cellId": self.id, "title": self.title})
        return result


class Street(Cell):
    """
    Street attributes you noted: owner, price, mortgage, ...
    """
    def __init__(self, cell_id: int, title: str, price: int):
        super().__init__(cell_id, title)
        self.price = int(price)
        self.owner_id: Optional[int] = None
        self.mortgaged: bool = False

    def buy(self, player: Player) -> None:
        if self.owner_id is not None:
            raise ValueError("already owned")
        player.wallet.pay(self.price)
        self.owner_id = player.id

    def on_land(self, game: "Game", player: Player) -> Dict[str, Any]:
        if self.owner_id is None:
            game.pending_prompt = {
                "type": "buy_prompt",
                "playerId": player.id,
                "cellId": self.id,
                "price": self.price,
                "title": self.title,
            }
            return {"type": "buy_prompt", "cellId": self.id, "price": self.price, "title": self.title}

        return {"type": "owned", "cellId": self.id, "ownerId": self.owner_id, "title": self.title}


# -------- Board --------

@dataclass
class Board:
    cells: List[Cell]

    def __post_init__(self):
        if len(self.cells) != 24:
            raise ValueError("Board must have exactly 24 cells")

    def cell(self, cell_id: int) -> Cell:
        return self.cells[cell_id]

    def to_dict(self) -> Dict[str, Any]:
        out: List[Dict[str, Any]] = []
        for c in self.cells:
            if isinstance(c, Street):
                out.append({
                    "id": c.id,
                    "type": "street",
                    "title": c.title,
                    "price": c.price,
                    "ownerId": c.owner_id,
                    "mortgaged": c.mortgaged,
                })
            elif isinstance(c, NewsCell):
                out.append({"id": c.id, "type": "news", "title": c.title})
            elif isinstance(c, StartCell):
                out.append({"id": c.id, "type": "start", "title": c.title})
            else:
                out.append({"id": c.id, "type": "cell", "title": c.title})
        return {"cells": out}
