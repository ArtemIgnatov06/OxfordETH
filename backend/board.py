from dataclasses import dataclass
from typing import Optional, List, Dict

@dataclass(frozen=True)
class Tile:
    id: int
    type: str               # 'property'|'chance'|'corner'|'tax'
    name: str
    price: Optional[float]  # как в твоём BoardData.js (может быть float)
    family: Optional[str] = None
    rent: Optional[int] = None
    subtype: Optional[str] = None


# Полная копия твоего BoardData.js по смыслу (IDs/типы/цены)
TILES: List[Tile] = [
    Tile(0,  "corner",  "START", None, subtype="go"),

    Tile(1,  "property","DOGE", 0.12, family="meme", rent=10),
    Tile(2,  "property","PEPE", 0.00001, family="meme", rent=5),

    Tile(3,  "chance",  "Chance", None),

    Tile(4,  "property","BONK", 0.00002, family="sol", rent=8),

    Tile(5,  "tax",     "Gas Fee", 100),

    Tile(6,  "corner",  "ACCOUNT BLOCKED", None, subtype="jail"),

    Tile(7,  "property","SOL", 145, family="sol", rent=14),
    Tile(8,  "property","JUP", 1.2, family="sol", rent=12),

    Tile(9,  "chance",  "Chance", None),

    Tile(10, "property","BNB", 580, family="bnb", rent=50),
    Tile(11, "property","CAKE", 2.5, family="bnb", rent=20),

    Tile(12, "corner",  "SYSTEM DOWN", None, subtype="parking"),

    Tile(13, "property","TWT", 1.1, family="bnb", rent=16),

    Tile(14, "property","ETH", 2400, family="eth", rent=200),
    Tile(15, "property","ARB", 1.1, family="eth", rent=15),
    Tile(16, "chance",  "Chance", None),
    Tile(17, "property","UNI", 7.5, family="eth", rent=18),

    Tile(18, "corner",  "SYSTEM BUG", None, subtype="gotojail"),

    Tile(19, "tax",     "Gas Fee", 100),

    Tile(20, "property","BTC", 65000, family="btc", rent=500),
    Tile(21, "property","WBTC", 64900, family="btc", rent=480),
    Tile(22, "chance",  "Chance", None),
    Tile(23, "property","STX", 1.8, family="btc", rent=25),
]

TILES_BY_ID: Dict[int, Tile] = {t.id: t for t in TILES}

BUYABLE_PROPERTY_IDS = {t.id for t in TILES if t.type == "property" and t.price is not None}
CHANCE_IDS = {t.id for t in TILES if t.type == "chance"}
BOARD_LEN = len(TILES)
