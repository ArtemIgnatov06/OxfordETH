from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Sequence
import json
import random
from pathlib import Path


# =========================
# Canonical layout (24 tiles, ids 0..23)
# Schema aligned with BoardData.js:
#   type: corner/property/chance/tax/action
#   subtype (corners only): go/jail/parking/gotojail
# =========================

DEFAULT_LAYOUT: list[dict[str, Any]] = [
    # --- BOTTOM ROW (Right to Left) ---
    {"id": 0, "type": "corner", "subtype": "go", "name": "START"},
    {"id": 1, "type": "property", "family": "meme", "name": "DOGE", "assetId": "DOGE", "price": 0.12, "rent": 10},
    {"id": 2, "type": "property", "family": "meme", "name": "PEPE", "assetId": "PEPE", "price": 0.00001, "rent": 5},
    {"id": 3, "type": "chance", "name": "Chance"},
    {"id": 4, "type": "property", "family": "meme", "name": "SHIB", "assetId": "SHIB", "price": 0.00002, "rent": 8},
    {"id": 5, "type": "tax", "name": "Gas Fee", "price": 50},

    # --- LEFT COLUMN (Bottom to Top) ---
    {"id": 6, "type": "corner", "subtype": "jail", "name": "JAIL"},
    {"id": 7, "type": "property", "family": "sol", "name": "SOL", "assetId": "SOL", "price": 145, "rent": 14},
    {"id": 8, "type": "property", "family": "sol", "name": "JUP", "assetId": "JUP", "price": 1.2, "rent": 12},
    {"id": 9, "type": "chance", "name": "Chance"},
    {"id": 10, "type": "property", "family": "bnb", "name": "BNB", "assetId": "BNB", "price": 580, "rent": 50},
    {"id": 11, "type": "property", "family": "bnb", "name": "CAKE", "assetId": "CAKE", "price": 2.5, "rent": 20},

    # --- TOP ROW (Left to Right) ---
    {"id": 12, "type": "corner", "subtype": "parking", "name": "HODL"},
    {"id": 13, "type": "property", "family": "eth", "name": "ETH", "assetId": "ETH", "price": 2400, "rent": 200},
    {"id": 14, "type": "property", "family": "eth", "name": "ARB", "assetId": "ARB", "price": 1.1, "rent": 15},
    {"id": 15, "type": "chance", "name": "Chance"},
    {"id": 16, "type": "property", "family": "eth", "name": "UNI", "assetId": "UNI", "price": 7.5, "rent": 18},
    {"id": 17, "type": "tax", "name": "Rug Pull", "price": 100},

    # --- RIGHT COLUMN (Top to Bottom) ---
    {"id": 18, "type": "corner", "subtype": "gotojail", "name": "GO TO JAIL"},
    {"id": 19, "type": "property", "family": "btc", "name": "BTC", "assetId": "BTC", "price": 65000, "rent": 500},
    {"id": 20, "type": "property", "family": "btc", "name": "WBTC", "assetId": "WBTC", "price": 64900, "rent": 480},
    {"id": 21, "type": "chance", "name": "Chance"},
    {"id": 22, "type": "property", "family": "btc", "name": "STX", "assetId": "STX", "price": 1.8, "rent": 25},
    {"id": 23, "type": "action", "name": "Airdrop"},
]


# =========================
# Models
# =========================

@dataclass
class Player:
    id: str
    position: int = 0
    jailed: int = 0
    frozen: int = 0


@dataclass(frozen=True)
class Action:
    type: str
    propertyId: Optional[str] = None
    reason: Optional[str] = None


# =========================
# BoardGame (in-memory prototype)
# =========================

class BoardGame:
    """
    Prototype in-memory game engine (no contracts).
    - Layout is DEFAULT_LAYOUT (24 tiles, ids 0..23)
    - Handles turns, dice, movement, gotojail->jail instant effect, and basic actions
    """

    def __init__(
        self,
        players: Sequence[Player],
        layout: Optional[list[dict[str, Any]]] = None,
        layout_path: Optional[str] = None,
        seed: int = 7
    ):
        if len(players) < 2:
            raise ValueError("Need at least 2 players")

        if layout_path is not None:
            layout = self.load_layout(layout_path)
        if layout is None:
            layout = DEFAULT_LAYOUT

        self.layout = self.validate_layout(layout)
        self.board_size = len(self.layout)

        self.players = list(players)
        self.turn_idx = 0
        self.rng = random.Random(seed)

        # off-chain ownership model (until contracts)
        self.owner_of: dict[str, str] = {}   # assetId -> playerId
        self.level_of: dict[str, int] = {}   # assetId -> level

        # state for UI
        self.last_dice: list[int] = [0, 0]
        self.last_landed: Optional[dict[str, Any]] = None
        self.available_actions: list[Action] = []
        self.log: list[str] = []

        self._recompute_actions()

    # ---------- layout helpers ----------

    @staticmethod
    def load_layout(path: str | Path) -> list[dict[str, Any]]:
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"board layout not found: {p.resolve()}")
        layout = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(layout, list) or not layout:
            raise ValueError("board_layout.json must be a non-empty JSON array")
        return layout

    @staticmethod
    def validate_layout(layout: list[dict[str, Any]]) -> list[dict[str, Any]]:
        ids = []
        for t in layout:
            if not isinstance(t, dict):
                raise ValueError("Each tile must be an object")
            if "id" not in t or "type" not in t:
                raise ValueError("Each tile must include 'id' and 'type'")
            if not isinstance(t["id"], int):
                raise ValueError("tile.id must be int")
            if not isinstance(t["type"], str):
                raise ValueError("tile.type must be str")
            ids.append(t["id"])

        if len(set(ids)) != len(ids):
            raise ValueError("tile ids must be unique")

        n = len(layout)
        if sorted(ids) != list(range(n)):
            raise ValueError(f"tile ids must be contiguous 0..{n-1}, got {sorted(ids)}")

        return layout

    # ---------- basic helpers ----------

    @property
    def current_player(self) -> Player:
        return self.players[self.turn_idx]

    def tile_at(self, pos: int) -> dict[str, Any]:
        return self.layout[pos % self.board_size]

    def find_corner_subtype_id(self, subtype: str) -> Optional[int]:
        for t in self.layout:
            if t.get("type") == "corner" and t.get("subtype") == subtype:
                return t["id"]
        return None

    # ---------- core flow ----------

    def roll_and_move(self) -> dict[str, Any]:
        p = self.current_player

        if p.frozen > 0:
            raise ValueError("Frozen: must skip turn")
        if p.jailed > 0:
            raise ValueError("Jailed: must skip turn")

        d1 = self.rng.randint(1, 6)
        d2 = self.rng.randint(1, 6)
        steps = d1 + d2

        old = p.position
        p.position = (p.position + steps) % self.board_size

        tile = self.tile_at(p.position)
        self.last_dice = [d1, d2]
        self.last_landed = dict(tile)

        self.log.append(f"{p.id} rolled {steps} ({d1}+{d2})")
        self.log.append(f"{p.id} moved {old} -> {p.position} landed on {tile.get('name', tile.get('type'))}")

        self._apply_instant_effects(p, tile)
        self._recompute_actions()
        return self.state()

    def _apply_instant_effects(self, p: Player, tile: dict[str, Any]) -> None:
        t = tile.get("type")

        # Corner: GO TO JAIL -> JAIL
        if t == "corner" and tile.get("subtype") == "gotojail":
            jail_id = self.find_corner_subtype_id("jail")
            if jail_id is not None:
                p.position = jail_id
                p.jailed = max(p.jailed, 1)
                jail_tile = self.tile_at(jail_id)
                self.last_landed = dict(jail_tile)
                self.log.append(f"{p.id} sent to JAIL (tile {jail_id})")

        # Tax/action are stubs for now (wallet logic later)
        if t == "tax":
            self.log.append(f"{p.id} hit tax tile '{tile.get('name')}' (stub)")
        if t == "action":
            self.log.append(f"{p.id} triggered action tile '{tile.get('name')}' (stub)")

    def end_turn(self) -> dict[str, Any]:
        p = self.current_player

        if p.frozen > 0:
            p.frozen -= 1
        if p.jailed > 0:
            p.jailed -= 1

        self.last_dice = [0, 0]
        self.last_landed = None

        self.turn_idx = (self.turn_idx + 1) % len(self.players)
        self.log.append(f"Next player: {self.current_player.id}")

        self._recompute_actions()
        return self.state()

    # ---------- UI actions ----------

    def _recompute_actions(self) -> None:
        p = self.current_player
        self.available_actions = []

        if p.frozen > 0:
            self.available_actions = [Action(type="SKIP_TURN", reason="FROZEN")]
            return
        if p.jailed > 0:
            self.available_actions = [Action(type="SKIP_TURN", reason="IN_JAIL")]
            return

        if self.last_landed is None:
            self.available_actions = [Action(type="ROLL_DICE")]
            return

        t = self.last_landed.get("type")

        if t == "chance":
            self.available_actions = [Action(type="DRAW_CHANCE"), Action(type="END_TURN")]
            return

        if t == "property":
            prop_id = self.last_landed.get("assetId")
            owner = self.owner_of.get(prop_id)

            if owner is None:
                self.available_actions = [Action(type="BUY_PROPERTY", propertyId=prop_id), Action(type="END_TURN")]
            elif owner != p.id:
                self.available_actions = [Action(type="PAY_RENT", propertyId=prop_id), Action(type="END_TURN")]
            else:
                self.available_actions = [Action(type="UPGRADE", propertyId=prop_id), Action(type="END_TURN")]
            return

        self.available_actions = [Action(type="END_TURN")]

    def perform_action(self, action_type: str, property_id: Optional[str] = None) -> dict[str, Any]:
        p = self.current_player

        if action_type in ("END_TURN", "SKIP_TURN"):
            return self.end_turn()

        if action_type == "DRAW_CHANCE":
            self.log.append(f"{p.id} drew chance (stub)")
            self._recompute_actions()
            return self.state()

        if action_type == "BUY_PROPERTY":
            if not property_id:
                raise ValueError("propertyId required")
            if self.owner_of.get(property_id) is not None:
                raise ValueError("Already owned")
            self.owner_of[property_id] = p.id
            self.level_of[property_id] = 0
            self.log.append(f"{p.id} bought {property_id} (stub)")
            self._recompute_actions()
            return self.state()

        if action_type == "PAY_RENT":
            if not property_id:
                raise ValueError("propertyId required")
            owner = self.owner_of.get(property_id)
            if owner is None:
                raise ValueError("Not owned")
            if owner == p.id:
                raise ValueError("Cannot pay yourself")
            self.log.append(f"{p.id} paid rent for {property_id} to {owner} (stub)")
            self._recompute_actions()
            return self.state()

        if action_type == "UPGRADE":
            if not property_id:
                raise ValueError("propertyId required")
            owner = self.owner_of.get(property_id)
            if owner != p.id:
                raise ValueError("Only owner can upgrade")
            self.level_of[property_id] = self.level_of.get(property_id, 0) + 1
            self.log.append(f"{p.id} upgraded {property_id} to level {self.level_of[property_id]} (stub)")
            self._recompute_actions()
            return self.state()

        raise ValueError(f"Unknown action: {action_type}")

    # ---------- API state ----------

    def state(self) -> dict[str, Any]:
        return {
            "boardSize": self.board_size,
            "players": [{"id": p.id, "position": p.position, "jailed": p.jailed, "frozen": p.frozen} for p in self.players],
            "currentPlayerId": self.current_player.id,
            "dice": self.last_dice,
            "lastLanded": self.last_landed,
            "availableActions": [a.__dict__ for a in self.available_actions],
            "log": self.log[-50:],
        }

