from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional


class CellType(Enum):
    START = "START"
    PROPERTY = "PROPERTY"
    JAIL = "JAIL"
    GO_TO_JAIL = "GO_TO_JAIL"
    SERVER_DOWN = "SERVER_DOWN"
    BUG = "BUG"
    CHANCE = "CHANCE"


class AssetFamily(Enum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"
    BNB = "BNB"
    MEME = "MEME"


@dataclass(frozen=True)
class Asset:
    id: str
    family: AssetFamily
    tier: int


@dataclass(frozen=True)
class Cell:
    index: int
    type: CellType
    asset: Optional[Asset] = None


@dataclass
class Player:
    player_id: str
    position: int = 0
    jailed_turns: int = 0
    frozen_turns: int = 0  # for SERVER_DOWN


class ActionType(Enum):
    ROLL_DICE = "ROLL_DICE"
    BUY_PROPERTY = "BUY_PROPERTY"
    PAY_RENT = "PAY_RENT"
    DRAW_CHANCE = "DRAW_CHANCE"
    END_TURN = "END_TURN"
    SKIP_TURN = "SKIP_TURN"  # if frozen/jailed


@dataclass(frozen=True)
class AvailableActions:
    # what UI should render (and what it should call)
    actions: list[ActionType]
    landed_cell: Optional[Cell] = None
    # if relevant:
    property_asset_id: Optional[str] = None
    reason: Optional[str] = None


class BoardGame:
    """
    Pure Web2 game orchestrator (no contracts).
    Responsibilities:
      - turn order
      - dice roll
      - movement + landing
      - determine which UI actions are available
    """

    def __init__(self, players: list[Player], seed: Optional[int] = None):
        if len(players) < 2:
            raise ValueError("Need at least 2 players for a game.")

        self.rng = random.Random(seed)
        self.players: list[Player] = players
        self.current_player_idx: int = 0

        self.cells: list[Cell] = []
        self._initialize_board()

        # Turn state
        self.has_rolled_this_turn: bool = False
        self.last_roll: Optional[int] = None  # 1..6 (prototype)
        self.last_landed_cell: Optional[Cell] = None

        # Prototype ownership (off-chain)
        # propertyId is asset.id (e.g., "BTC2") for simplicity
        self.owner_of: dict[str, str] = {}  # asset_id -> player_id

    # ---------- Board setup ----------

    def _create_assets(self) -> dict[str, Asset]:
        return {
            "BTC1": Asset("BTC1", AssetFamily.BTC, 1),
            "BTC2": Asset("BTC2", AssetFamily.BTC, 2),
            "BTC3": Asset("BTC3", AssetFamily.BTC, 3),

            "ETH1": Asset("ETH1", AssetFamily.ETH, 1),
            "ETH2": Asset("ETH2", AssetFamily.ETH, 2),
            "ETH3": Asset("ETH3", AssetFamily.ETH, 3),

            "SOL1": Asset("SOL1", AssetFamily.SOL, 1),
            "SOL2": Asset("SOL2", AssetFamily.SOL, 2),
            "SOL3": Asset("SOL3", AssetFamily.SOL, 3),

            "BNB1": Asset("BNB1", AssetFamily.BNB, 1),
            "BNB2": Asset("BNB2", AssetFamily.BNB, 2),
            "BNB3": Asset("BNB3", AssetFamily.BNB, 3),

            "MEME1": Asset("MEME1", AssetFamily.MEME, 1),
            "MEME2": Asset("MEME2", AssetFamily.MEME, 2),
        }

    def _initialize_board(self) -> None:
        assets = self._create_assets()
        idx = 0

        def add(cell_type: CellType, asset: Optional[Asset] = None):
            nonlocal idx
            self.cells.append(Cell(idx, cell_type, asset))
            idx += 1

        add(CellType.START)

        # BTC family
        add(CellType.PROPERTY, assets["BTC1"])
        add(CellType.PROPERTY, assets["BTC2"])
        add(CellType.PROPERTY, assets["BTC3"])

        add(CellType.CHANCE)       # chance #1
        add(CellType.SERVER_DOWN)  # server down

        # ETH family
        add(CellType.PROPERTY, assets["ETH1"])
        add(CellType.PROPERTY, assets["ETH2"])
        add(CellType.PROPERTY, assets["ETH3"])

        add(CellType.CHANCE)       # chance #2
        add(CellType.BUG)          # bug -> jail
        add(CellType.JAIL)         # jail

        # BNB family
        add(CellType.PROPERTY, assets["BNB1"])
        add(CellType.PROPERTY, assets["BNB2"])
        add(CellType.PROPERTY, assets["BNB3"])

        add(CellType.CHANCE)       # chance #3

        # SOL family
        add(CellType.PROPERTY, assets["SOL1"])
        add(CellType.PROPERTY, assets["SOL2"])
        add(CellType.PROPERTY, assets["SOL3"])

        # Meme
        add(CellType.PROPERTY, assets["MEME1"])
        add(CellType.PROPERTY, assets["MEME2"])

        add(CellType.CHANCE)       # chance #4
        add(CellType.GO_TO_JAIL)   # go to jail

    # ---------- Turn helpers ----------

    @property
    def current_player(self) -> Player:
        return self.players[self.current_player_idx]

    def get_cell(self, position: int) -> Cell:
        return self.cells[position % len(self.cells)]

    # ---------- Core gameplay (no contracts) ----------

    def roll_dice(self) -> int:
        """
        Rolls a 1d6 dice for movement (prototype).
        Enforces: can roll once per turn and cannot roll if frozen/jailed.
        """
        p = self.current_player

        if p.frozen_turns > 0:
            raise RuntimeError("Player is frozen (SERVER_DOWN) and must skip turn.")
        if p.jailed_turns > 0:
            raise RuntimeError("Player is jailed and must skip turn.")
        if self.has_rolled_this_turn:
            raise RuntimeError("Already rolled dice this turn.")

        roll = self.rng.randint(1, 6)
        self.has_rolled_this_turn = True
        self.last_roll = roll
        return roll

    def move_current_player(self) -> Cell:
        """
        Applies movement based on last roll.
        Returns landed cell. Must roll before moving.
        """
        if not self.has_rolled_this_turn or self.last_roll is None:
            raise RuntimeError("Roll dice before moving.")

        p = self.current_player
        p.position = (p.position + self.last_roll) % len(self.cells)

        landed = self.get_cell(p.position)
        self.last_landed_cell = landed

        # Apply immediate cell effects that change state (still Web2)
        self._apply_instant_cell_effects(p, landed)

        return self.last_landed_cell

    def _apply_instant_cell_effects(self, p: Player, cell: Cell) -> None:
        # BUG or GO_TO_JAIL sends to jail
        if cell.type in (CellType.BUG, CellType.GO_TO_JAIL):
            self._send_to_jail(p)

        # SERVER_DOWN freezes next turn (example: 1 turn)
        if cell.type == CellType.SERVER_DOWN:
            p.frozen_turns = max(p.frozen_turns, 1)

    def _send_to_jail(self, p: Player) -> None:
        jail_idx = next(i for i, c in enumerate(self.cells) if c.type == CellType.JAIL)
        p.position = jail_idx
        p.jailed_turns = max(p.jailed_turns, 1)
        self.last_landed_cell = self.get_cell(p.position)

    # ---------- UI action computation ----------

    def get_available_actions(self) -> AvailableActions:
        """
        This is what your website uses to decide which buttons to show.
        """
        p = self.current_player

        # If frozen/jailed: only skip/end turn
        if p.frozen_turns > 0:
            return AvailableActions(
                actions=[ActionType.SKIP_TURN],
                landed_cell=self.get_cell(p.position),
                reason="SERVER_DOWN"
            )
        if p.jailed_turns > 0:
            return AvailableActions(
                actions=[ActionType.SKIP_TURN],
                landed_cell=self.get_cell(p.position),
                reason="IN_JAIL"
            )

        # If haven't rolled yet: show roll dice
        if not self.has_rolled_this_turn:
            return AvailableActions(actions=[ActionType.ROLL_DICE])

        # If rolled but not moved: you likely want UI to call move
        if self.last_landed_cell is None:
            # You can model MOVE as an action, but simplest: after roll, call move.
            return AvailableActions(actions=[ActionType.END_TURN], reason="Call move_current_player() after roll")

        # After landing, show contextual actions
        cell = self.last_landed_cell

        if cell.type == CellType.CHANCE:
            return AvailableActions(actions=[ActionType.DRAW_CHANCE, ActionType.END_TURN], landed_cell=cell)

        if cell.type == CellType.PROPERTY and cell.asset is not None:
            asset_id = cell.asset.id
            owner = self.owner_of.get(asset_id)

            if owner is None:
                return AvailableActions(
                    actions=[ActionType.BUY_PROPERTY, ActionType.END_TURN],
                    landed_cell=cell,
                    property_asset_id=asset_id
                )
            elif owner != p.player_id:
                return AvailableActions(
                    actions=[ActionType.PAY_RENT, ActionType.END_TURN],
                    landed_cell=cell,
                    property_asset_id=asset_id
                )

        # Default: can end turn
        return AvailableActions(actions=[ActionType.END_TURN], landed_cell=cell)

    # ---------- Minimal transaction stubs (still Web2) ----------

    def buy_property(self, asset_id: str) -> None:
        """
        Prototype: sets owner. No money logic yet.
        """
        p = self.current_player
        if asset_id in self.owner_of:
            raise RuntimeError("Already owned.")
        self.owner_of[asset_id] = p.player_id

    def pay_rent(self, asset_id: str) -> None:
        """
        Prototype placeholder: no money yet.
        """
        owner = self.owner_of.get(asset_id)
        if owner is None:
            raise RuntimeError("Property not owned.")
        if owner == self.current_player.player_id:
            raise RuntimeError("Cannot pay rent to yourself.")
        # money transfer will be added later

    def end_turn(self) -> None:
        """
        Advances to next player, handles jail/freeze counters, resets turn state.
        """
        p = self.current_player

        # decrement statuses (end of player's turn)
        if p.frozen_turns > 0:
            p.frozen_turns -= 1
        if p.jailed_turns > 0:
            p.jailed_turns -= 1

        # reset turn state
        self.has_rolled_this_turn = False
        self.last_roll = None
        self.last_landed_cell = None

        # next player
        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
