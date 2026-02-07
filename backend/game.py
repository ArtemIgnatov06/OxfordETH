from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
import random
import time
import uuid

from board import BOARD_LEN, TILES_BY_ID, BUYABLE_PROPERTY_IDS, CHANCE_IDS


OfferType = Literal["sell", "buy"]

@dataclass
class Message:
    user: str
    text: str

@dataclass
class TradeOffer:
    id: str
    type: OfferType
    from_player: int
    to_player: int
    tile_id: int
    price_fc: int
    created_at: int

    def to_front(self):
        return {
            "id": self.id,
            "type": self.type,
            "from": self.from_player,
            "to": self.to_player,
            "tileId": self.tile_id,
            "priceFC": self.price_fc,
            "createdAt": self.created_at,
        }

@dataclass
class GameState:
    players_count: int = 4
    dice: List[int] = field(default_factory=lambda: [1, 1])
    player_pos: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    active_player: int = 0

    # tileId -> ownerIndex
    ownership: Dict[int, int] = field(default_factory=dict)

    # buyPrompt: {tileId, playerIndex} or None
    buy_prompt: Optional[Dict] = None

    # FlareCoins balances
    balances: List[int] = field(default_factory=lambda: [4200, 1337, 777, 9001])

    # trade offers
    trade_offers: List[TradeOffer] = field(default_factory=list)

    messages: List[Message] = field(default_factory=lambda: [Message("System", "Welcome to FlarePoly Testnet!")])

    def reset(self):
        self.dice = [1, 1]
        self.player_pos = [0] * self.players_count
        self.active_player = 0
        self.ownership = {}
        self.buy_prompt = None
        self.balances = [4200, 1337, 777, 9001][: self.players_count]
        self.trade_offers = []
        self.messages = [Message("System", "Welcome to FlarePoly Testnet!")]

    # ----- helpers -----
    def add_message(self, user: str, text: str):
        self.messages.append(Message(user, text))

    def incoming_offers_for_active(self) -> List[TradeOffer]:
        return [o for o in self.trade_offers if o.to_player == self.active_player]

    def next_player(self):
        self.active_player = (self.active_player + 1) % self.players_count

    def _guard_turn_not_blocked(self):
        if self.buy_prompt is not None:
            raise ValueError("Blocked: buyPrompt pending")
        if len(self.incoming_offers_for_active()) > 0:
            raise ValueError("Blocked: incoming offers pending")

    def _roll_dice(self) -> List[int]:
        d1 = random.randint(1, 6)
        d2 = random.randint(1, 6)
        self.dice = [d1, d2]
        return self.dice

    def _move(self, player_index: int, steps: int) -> int:
        self.player_pos[player_index] = (self.player_pos[player_index] + steps) % BOARD_LEN
        return self.player_pos[player_index]

    def _chance_news(self):
        news = random.choice([
            "Breaking: memecoin season is back.",
            "News: gas fee spike. Everyone panics (but nothing happens).",
            "Alert: whale moved funds. Market shrugs.",
            "Update: protocol upgrade scheduled. Chat explodes.",
            "Rumor: new listing coming. Everyone buys top.",
        ])
        self.add_message("News", news)

    # ----- actions -----
    def roll(self):
        self._guard_turn_not_blocked()

        d1, d2 = self._roll_dice()
        steps = d1 + d2
        p = self.active_player

        self.add_message("Player", f"P{p+1} rolled {steps} ({d1} + {d2})")

        final_pos = self._move(p, steps)
        tile = TILES_BY_ID[final_pos]

        # chance -> news
        if final_pos in CHANCE_IDS:
            self._chance_news()
            self.next_player()
            return

        # property buy prompt (only if not owned)
        if final_pos in BUYABLE_PROPERTY_IDS and final_pos not in self.ownership:
            self.buy_prompt = {"tileId": final_pos, "playerIndex": p}
            return

        # tax/corner -> no-op for now
        self.next_player()

    def buy(self, tile_id: Optional[int] = None):
        if self.buy_prompt is None:
            raise ValueError("No buy prompt")

        prompt_tile = self.buy_prompt["tileId"]
        p = self.buy_prompt["playerIndex"]

        if p != self.active_player:
            raise ValueError("Not your buy prompt")

        if tile_id is not None and tile_id != prompt_tile:
            raise ValueError("Tile mismatch")

        if prompt_tile in self.ownership:
            self.buy_prompt = None
            self.add_message("System", "Buy failed: already owned")
            self.next_player()
            return

        tile = TILES_BY_ID[prompt_tile]
        # В твоём фронте покупка за $ (не FC) — просто фиксируем ownership
        self.ownership[prompt_tile] = p
        self.add_message("System", f"P{p+1} bought {tile.name} for ${tile.price}")
        self.buy_prompt = None
        self.next_player()

    def skip_buy(self):
        if self.buy_prompt is None:
            raise ValueError("No buy prompt")

        p = self.buy_prompt["playerIndex"]
        tile = TILES_BY_ID[self.buy_prompt["tileId"]]
        self.add_message("System", f"P{p+1} skipped {tile.name}")

        self.buy_prompt = None
        self.next_player()

    # ----- offers -----
    def create_offer(self, offer_type: OfferType, to_player: int, tile_id: int, price_fc: int):
        # only on your turn and not blocked
        self._guard_turn_not_blocked()

        if to_player == self.active_player:
            raise ValueError("Cannot target yourself")
        if tile_id not in BUYABLE_PROPERTY_IDS:
            raise ValueError("Tile not tradable")
        if price_fc <= 0:
            raise ValueError("Price must be > 0")

        tile = TILES_BY_ID[tile_id]
        owner = self.ownership.get(tile_id)

        if offer_type == "sell":
            if owner != self.active_player:
                raise ValueError("You can sell only your own tile")
        else:  # buy
            if owner is None:
                raise ValueError("Tile not owned (buy it on landing)")
            if owner != to_player:
                raise ValueError("Target must be the current owner")

        offer = TradeOffer(
            id=str(uuid.uuid4()),
            type=offer_type,
            from_player=self.active_player,
            to_player=to_player,
            tile_id=tile_id,
            price_fc=int(price_fc),
            created_at=int(time.time() * 1000),
        )
        self.trade_offers.insert(0, offer)

        if offer_type == "sell":
            self.add_message("System", f"P{offer.from_player+1} offers to SELL {tile.name} to P{offer.to_player+1} for {offer.price_fc} FC")
        else:
            self.add_message("System", f"P{offer.from_player+1} offers to BUY {tile.name} from P{offer.to_player+1} for {offer.price_fc} FC")

    def _find_offer(self, offer_id: str) -> TradeOffer:
        for o in self.trade_offers:
            if o.id == offer_id:
                return o
        raise ValueError("Offer not found")

    def accept_offer(self, offer_id: str):
        offer = self._find_offer(offer_id)

        if self.active_player != offer.to_player:
            raise ValueError("Accept offers only on your turn")

        tile = TILES_BY_ID[offer.tile_id]
        current_owner = self.ownership.get(offer.tile_id)

        seller = offer.from_player if offer.type == "sell" else offer.to_player
        buyer = offer.to_player if offer.type == "sell" else offer.from_player

        # validate ownership still same
        if current_owner != seller:
            self._remove_offer(offer_id)
            self.add_message("System", f"Offer invalid: tile owner changed for {tile.name}")
            return

        if self.balances[buyer] < offer.price_fc:
            raise ValueError(f"Deal failed: P{buyer+1} has not enough FC")

        # transfer FC
        self.balances[buyer] -= offer.price_fc
        self.balances[seller] += offer.price_fc

        # transfer tile ownership
        self.ownership[offer.tile_id] = buyer

        self.add_message("System", f"Deal: {tile.name} P{seller+1} → P{buyer+1} for {offer.price_fc} FC")

        self._remove_offer(offer_id)
        self.next_player()

    def decline_offer(self, offer_id: str):
        offer = self._find_offer(offer_id)
        if self.active_player != offer.to_player:
            raise ValueError("Decline offers only on your turn")

        self.add_message("System", f"Offer declined by P{offer.to_player+1}")
        self._remove_offer(offer_id)
        self.next_player()

    def _remove_offer(self, offer_id: str):
        self.trade_offers = [o for o in self.trade_offers if o.id != offer_id]

    # ----- serialization -----
    def to_front(self):
        return {
            "dice": self.dice,
            "playerPos": self.player_pos,
            "activePlayer": self.active_player,
            "ownership": {str(k): v for k, v in self.ownership.items()},
            "buyPrompt": self.buy_prompt,
            "balances": self.balances,
            "tradeOffers": [o.to_front() for o in self.trade_offers],
            "messages": [{"user": m.user, "text": m.text} for m in self.messages],
        }
