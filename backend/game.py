from __future__ import annotations
from typing import Dict, Any, List, Optional
import random

from models import Player, Wallet, Board, Cell, Street, NewsCell, StartCell, ChanceDeck, TradeOffer

class Game:
    def __init__(self, players: List[Player], board: Board, chance: ChanceDeck):
        self.players: Dict[int, Player] = {p.id: p for p in players}
        self.board = board
        self.chance = chance

        self.active_player_id: int = players[0].id if players else 0
        self.dice: List[int] = [1, 1]
        self.messages: List[Dict[str, str]] = [{"user": "System", "text": "Game created"}]

        self.pending_prompt: Optional[Dict[str, Any]] = None
        self.trade_offers: List[TradeOffer] = []

    def log(self, text: str) -> None:
        self.messages.append({"user": "System", "text": text})
        if len(self.messages) > 400:
            self.messages = self.messages[-400:]

    def active_player(self) -> Player:
        return self.players[self.active_player_id]

    def next_turn(self) -> None:
        ids = sorted(self.players.keys())
        idx = ids.index(self.active_player_id)
        self.active_player_id = ids[(idx + 1) % len(ids)]

    def roll_and_move(self, player_id: int) -> Dict[str, Any]:
        if player_id != self.active_player_id:
            raise ValueError("not your turn")
        if self.pending_prompt is not None:
            raise ValueError("resolve pending prompt first")

        d1, d2 = random.randint(1, 6), random.randint(1, 6)
        self.dice = [d1, d2]
        steps = d1 + d2

        p = self.players[player_id]
        start = p.pos
        p.pos = (p.pos + steps) % 24

        self.log(f"{p.name} rolled {steps} ({d1}+{d2}) and moved {start} -> {p.pos}")

        event = self.board.cell(p.pos).on_land(self, p)

        if self.pending_prompt is None:
            self.next_turn()

        return {"movement": {"start": start, "final": p.pos, "steps": steps}, "event": event}

    def buy_pending(self, player_id: int) -> None:
        if not self.pending_prompt or self.pending_prompt.get("type") != "buy_prompt":
            raise ValueError("no buy prompt")
        if self.pending_prompt["playerId"] != player_id:
            raise ValueError("not your buy prompt")

        cell_id = self.pending_prompt["cellId"]
        cell = self.board.cell(cell_id)
        if not isinstance(cell, Street):
            raise ValueError("cell is not a street")

        p = self.players[player_id]
        cell.buy(p)
        self.log(f"{p.name} bought {cell.title} for {cell.price} FC")

        self.pending_prompt = None
        self.next_turn()

    def skip_pending(self, player_id: int) -> None:
        if not self.pending_prompt:
            raise ValueError("no pending prompt")
        if self.pending_prompt.get("playerId") != player_id:
            raise ValueError("not your pending prompt")

        self.log(f"{self.players[player_id].name} skipped buy on cell {self.pending_prompt.get('cellId')}")
        self.pending_prompt = None
        self.next_turn()

    def create_offer(self, offer: TradeOffer) -> None:
        if offer.from_player == offer.to_player:
            raise ValueError("from == to")
        if offer.price <= 0:
            raise ValueError("price must be > 0")

        cell = self.board.cell(offer.cell_id)
        if not isinstance(cell, Street):
            raise ValueError("only streets are tradable")

        if offer.type == "sell":
            if cell.owner_id != offer.from_player:
                raise ValueError("seller must own the street")
        else:  # buy
            if cell.owner_id != offer.to_player:
                raise ValueError("target must be current owner")

        self.trade_offers.insert(0, offer)
        self.log(f"Offer: {offer.type} cell#{offer.cell_id} for {offer.price} FC")

    def accept_offer(self, offer_id: str, player_id: int) -> None:
        offer = next((o for o in self.trade_offers if o.id == offer_id), None)
        if not offer:
            raise ValueError("offer not found")
        if player_id != self.active_player_id:
            raise ValueError("accept only on your turn")
        if offer.to_player != player_id:
            raise ValueError("only recipient can accept")

        cell = self.board.cell(offer.cell_id)
        if not isinstance(cell, Street):
            raise ValueError("invalid offer: not a street")

        if offer.type == "sell":
            seller_id, buyer_id = offer.from_player, offer.to_player
        else:
            buyer_id, seller_id = offer.from_player, offer.to_player

        if cell.owner_id != seller_id:
            self.trade_offers = [o for o in self.trade_offers if o.id != offer_id]
            raise ValueError("owner changed; offer removed")

        buyer = self.players[buyer_id]
        seller = self.players[seller_id]

        buyer.wallet.pay(offer.price)
        seller.wallet.receive(offer.price)
        cell.owner_id = buyer_id

        self.trade_offers = [o for o in self.trade_offers if o.id != offer_id]
        self.log(f"Deal: {cell.title} {seller.name} -> {buyer.name} for {offer.price} FC")

        self.next_turn()

    def to_state(self) -> Dict[str, Any]:
        return {
            "activePlayerId": self.active_player_id,
            "dice": self.dice,
            "players": [
                {"id": p.id, "name": p.name, "pos": p.pos, "balance": p.wallet.balance}
                for p in self.players.values()
            ],
            "board": self.board.to_dict(),
            "pendingPrompt": self.pending_prompt,
            "tradeOffers": [
                {
                    "id": o.id,
                    "type": o.type,
                    "fromPlayer": o.from_player,
                    "toPlayer": o.to_player,
                    "cellId": o.cell_id,
                    "price": o.price,
                }
                for o in self.trade_offers
            ],
            "messages": self.messages,
        }
