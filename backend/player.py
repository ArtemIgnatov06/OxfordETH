from dataclasses import dataclass
from wallet import Wallet

@dataclass
class Player:
    id: int
    name: str
    pos: int
    wallet: Wallet
