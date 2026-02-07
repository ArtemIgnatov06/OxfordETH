from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any
import random

from .player import Player

@dataclass
class ChanceEvent:
    delta: int
    text: str

class ChanceDeck:
    """
    Your notebook: '4 classes call action(): news'
    This is the 'news/chance' action generator.
    """
    def __init__(self, seed: int | None = None):
        self.rng = random.Random(seed)
        self.events = [
            ChanceEvent(+250, "Airdrop reward"),
            ChanceEvent(+150, "Validator reward"),
            ChanceEvent(+100, "Referral bonus"),
            ChanceEvent(-100, "Gas spike fee"),
            ChanceEvent(-200, "Slashed for downtime"),
        ]

    def draw(self) -> ChanceEvent:
        return self.rng.choice(self.events)

    def apply(self, player: Player) -> Dict[str, Any]:
        event = self.draw()
        if event.delta >= 0:
            player.wallet.receive(event.delta)
        else:
            player.wallet.pay(-event.delta)

        return {"type": "news", "delta": event.delta, "text": event.text}
