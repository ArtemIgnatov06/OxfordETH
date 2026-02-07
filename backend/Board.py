from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random
from typing import Optional, Protocol, Sequence


# =========================
# Board domain model
# =========================

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


class ActionType(Enum):
    ROLL_DICE = "ROLL_DICE"
    DRAW_CHANCE = "DRAW_CHANCE"
    BUY_PROPERTY = "BUY_PROPERTY"
    PAY_RENT = "PAY_RENT"
    UPGRADE = "UPGRADE"
    END_TURN = "END_TURN"
    SKIP_TURN = "SKIP_TURN"


@dataclass(frozen=True)
class AvailableActions:
    """
    What the UI should show as buttons + useful context.
    Board computes these using mostly contract reads.
    """
    actions: list[ActionType]
    landed_cell: Optional[Cell] = None
    property_id: Optional[str] = None

    # "truth" rendered from chain reads:
    owner: Optional[str] = None
    level: Optional[int] = None
    player_balance: Optional[int] = None
    asset_price: Optional[int] = None
    property_price: Optional[int] = None

    reason: Optional[str] = None


# =========================
# External dependencies (interfaces only)
# =========================

class PlayerView(Protocol):
    """
    Minimal interface Board expects from your Player class/module.
    Board does NOT define Player; it only needs these fields.
    """
    player_id: str            # can be wallet address for now
    position: int
    jailed_turns: int
    frozen_turns: int


class GameReader(Protocol):
    """
    READS from GameInstance (contract) to render truth.
    Backed by web3.py later.
    """
    def get_asset_price(self, asset_id: str) -> int: ...
    def get_property_price(self, property_id: str) -> int: ...
    def owner_of(self, property_id: str) -> Optional[str]: ...
    def level_of(self, property_id: str) -> int: ...
    def balance_of(self, player_id: str) -> int: ...


class TxRouter(Protocol):
    """
    Routes UI clicks to Transaction layer (which sends contract txs).
    Board does NOT implement tx logic; it just calls these.
    Returns tx hash string (or any identifier you choose).
    """
    def buy_property(self, property_id: str, player_id: str) -> str: ...
    def pay_rent(self, property_id: str, player_id: str) -> str: ...
    def upgrade_property(self, property_id: str, player_id: str) -> str: ...


# =========================
# BoardGame (Board-only)
# =========================

class BoardGame:
    """
    Off-chain responsibilities:
      • Builds board layout (cells: start/jail/bug/server down/properties).
      • Maintains turn order, dice, movement, “you landed here”.
      • Determines which action buttons should be presented.

    Contract usage:
      • Mostly reads from GameReader to render truth:
          - getAssetPrice(assetId) / getPropertyPrice(propertyId)
          - ownerOf(propertyId), levelOf(propertyId)
          - balanceOf(player)
      • Triggers txs indirectly through TxRouter:
          - “Buy”, “Pay rent”, “Upgrade” route to TxRouter.
    """

    def __init__(
        self,
        players: Sequence[PlayerView],
        game_reader: GameReader,
        tx_router: TxRouter,
        seed: Optional[int] = None
    ):
        if len(players) < 2:
            raise ValueError("Need at least 2 players.")

        self.players: list[PlayerView] = list(players)
        self.game: GameReader = game_reader
        self.tx: TxRouter = tx_router

        self.rng = random.Random(seed)

        self.current_player_idx: int = 0
        self.cells: list[Cell] = []
        self._initialize_board()

        # turn state
        self.has_rolled_this_turn: bool = False
        self.last_roll: Optional[int] = None
        self.last_landed_cell: Optional[Cell] = None

    # ---------- Board init ----------

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

    # ---------- Helpers ----------

    @property
    def size(self) -> int:
        return len(self.cells)

    @property
    def current_player(self) -> PlayerView:
        return self.players[self.current_player_idx]

    def get_cell(self, position: int) -> Cell:
        return self.cells[position % len(self.cells)]

    # ---------- Dice + Movement ----------

    def roll_dice(self) -> int:
        """
        1d6 dice for movement (prototype).
        Dice used ONLY for movement (as you specified).
        """
        p = self.current_player

        if p.frozen_turns > 0:
            raise RuntimeError("Frozen (SERVER_DOWN): must skip turn.")
        if p.jailed_turns > 0:
            raise RuntimeError("Jailed: must skip turn.")
        if self.has_rolled_this_turn:
            raise RuntimeError("Already rolled this turn.")

        roll = self.rng.randint(1, 6)
        self.has_rolled_this_turn = True
        self.last_roll = roll
        return roll

    def move_current_player(self) -> Cell:
        """
        Moves current player by last_roll and applies immediate cell effects.
        """
        if not self.has_rolled_this_turn or self.last_roll is None:
            raise RuntimeError("Roll dice before moving.")

        p = self.current_player
        p.position = (p.position + self.last_roll) % len(self.cells)
        landed = self.get_cell(p.position)
        self.last_landed_cell = landed

        # Apply off-chain immediate effects (still board logic)
        self._apply_instant_cell_effects(p, landed)
        return self.last_landed_cell

    def _apply_instant_cell_effects(self, p: PlayerView, cell: Cell) -> None:
        # BUG or GO_TO_JAIL sends to jail
        if cell.type in (CellType.BUG, CellType.GO_TO_JAIL):
            self._send_to_jail(p)

        # SERVER_DOWN freezes next turn (example: 1 turn)
        if cell.type == CellType.SERVER_DOWN:
            p.frozen_turns = max(p.frozen_turns, 1)

    def _send_to_jail(self, p: PlayerView) -> None:
        jail_idx = next(i for i, c in enumerate(self.cells) if c.type == CellType.JAIL)
        p.position = jail_idx
        p.jailed_turns = max(p.jailed_turns, 1)
        self.last_landed_cell = self.get_cell(p.position)

    # ---------- UI action computation (with contract reads) ----------

    def get_available_actions(self) -> AvailableActions:
        """
        UI uses this to decide which buttons to show.
        Uses GameReader reads to render truth and determine relevant tx actions.
        """
        p = self.current_player

        # frozen/jailed => only SKIP
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

        # not rolled => ROLL
        if not self.has_rolled_this_turn:
            return AvailableActions(actions=[ActionType.ROLL_DICE])

        # rolled but not moved (depends on how your UI is wired)
        if self.last_landed_cell is None:
            return AvailableActions(
                actions=[ActionType.END_TURN],
                reason="Call move_current_player() after roll"
            )

        cell = self.last_landed_cell

        if cell.type == CellType.CHANCE:
            return AvailableActions(
                actions=[ActionType.DRAW_CHANCE, ActionType.END_TURN],
                landed_cell=cell
            )

        if cell.type == CellType.PROPERTY and cell.asset is not None:
            prop_id = cell.asset.id

            owner = self.game.owner_of(prop_id)
            level = self.game.level_of(prop_id)
            bal = self.game.balance_of(p.player_id)

            # pricing reads (useful for UI panels)
            asset_price = self.game.get_asset_price(cell.asset.id)
            prop_price = self.game.get_property_price(prop_id)

            if owner is None:
                return AvailableActions(
                    actions=[ActionType.BUY_PROPERTY, ActionType.END_TURN],
                    landed_cell=cell,
                    property_id=prop_id,
                    owner=owner,
                    level=level,
                    player_balance=bal,
                    asset_price=asset_price,
                    property_price=prop_price
                )

            if owner.lower() != p.player_id.lower():
                return AvailableActions(
                    actions=[ActionType.PAY_RENT, ActionType.END_TURN],
                    landed_cell=cell,
                    property_id=prop_id,
                    owner=owner,
                    level=level,
                    player_balance=bal,
                    asset_price=asset_price,
                    property_price=prop_price
                )

            # owned by the player => allow UPGRADE
            return AvailableActions(
                actions=[ActionType.UPGRADE, ActionType.END_TURN],
                landed_cell=cell,
                property_id=prop_id,
                owner=owner,
                level=level,
                player_balance=bal,
                asset_price=asset_price,
                property_price=prop_price
            )

        return AvailableActions(actions=[ActionType.END_TURN], landed_cell=cell)

    # ---------- Button click routing (Board -> TxRouter) ----------

    def click_buy(self, property_id: str) -> str:
        """
        UI 'Buy' button -> routes to Transaction layer -> contract buyProperty(propertyId)
        """
        return self.tx.buy_property(property_id=property_id, player_id=self.current_player.player_id)

    def click_pay_rent(self, property_id: str) -> str:
        """
        UI 'Pay rent' button -> routes to Transaction layer -> contract payRent(propertyId)
        """
        return self.tx.pay_rent(property_id=property_id, player_id=self.current_player.player_id)

    def click_upgrade(self, property_id: str) -> str:
        """
        UI 'Upgrade' button -> routes to Transaction layer -> contract upgradeProperty(propertyId)
        """
        return self.tx.upgrade_property(property_id=property_id, player_id=self.current_player.player_id)

    # ---------- Turn progression ----------

    def end_turn(self) -> None:
        """
        Advances to next player, decrements jail/freeze counters, resets turn state.
        """
        p = self.current_player

        if p.frozen_turns > 0:
            p.frozen_turns -= 1
        if p.jailed_turns > 0:
            p.jailed_turns -= 1

        self.has_rolled_this_turn = False
        self.last_roll = None
        self.last_landed_cell = None

        self.current_player_idx = (self.current_player_idx + 1) % len(self.players)
