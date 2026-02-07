from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
import crypto_random
import time
import uuid
import random
from board import BOARD_LEN, TILES_BY_ID, BUYABLE_PROPERTY_IDS, CHANCE_IDS
from chance import ChanceDeck
from wallet import Wallet
from player import Player

OfferType = Literal["sell", "buy"]
START_TILE_ID = 0
START_BONUS_FC = 200
PRISON_WAIT_TURNS = 1
PRISON_TILE_ID = 6        # waits / skips next turn
GOTO_PRISON_TILE_ID = 18


@dataclass
class Message:
    user: str
    text: str
    type: str = "chat"          # "chat" | "system" | "news" ...
    delta: Optional[int] = None # только для news/chance
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
    eliminated: List[bool] = field(default_factory=lambda: [False, False, False, False])
    game_over: bool = False
    winner: Optional[int] = None
    chance_deck: ChanceDeck = field(default_factory=ChanceDeck)
    skip_turns: List[int] = field(default_factory=lambda: [0, 0, 0, 0])

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

        self.eliminated = [False] * self.players_count
        self.game_over = False
        self.winner = None
        self.skip_turns = [0] * self.players_count

    # ----- helpers -----

    def _alive_players(self) -> List[int]:
        return [i for i in range(self.players_count) if not self.eliminated[i]]

    def _advance_to_next_alive(self):
        """Move active_player forward until it points at a non-eliminated player.
        Assumes there is at least 1 alive player.
        """
        for _ in range(self.players_count):
            if not self.eliminated[self.active_player]:
                return
            self.active_player = (self.active_player + 1) % self.players_count

    def _check_bankruptcy_and_win(self):
        """Eliminate players with <= 0 FC and declare winner if only one remains."""
        # Eliminate anyone who is broke
        for i in range(self.players_count):
            if not self.eliminated[i] and self.balances[i] <= 0:
                self.eliminated[i] = True
                self.add_message("System", f"P{i+1} is BANKRUPT and out of the game")

        alive = self._alive_players()

        if len(alive) == 1:
            self.game_over = True
            self.winner = alive[0]
            self.add_message("System", f"P{self.winner+1} wins! 🎉")
            # Unblock any pending UI prompts/offers so frontend doesn’t get stuck
            self.buy_prompt = None
            self.trade_offers = []
            return

        # If current active got eliminated, move to next alive
        if self.eliminated[self.active_player] and len(alive) > 0:
            self._advance_to_next_alive()


    def add_message(self, user: str, text: str, msg_type: str = "chat", delta: int | None = None):
        self.messages.append(Message(user, text, msg_type, delta))


    def incoming_offers_for_active(self) -> List[TradeOffer]:
        return [o for o in self.trade_offers if o.to_player == self.active_player]

    def next_player(self):
        if self.game_over:
            return
        self.active_player = (self.active_player + 1) % self.players_count
        self._advance_to_next_alive()

    def _guard_turn_not_blocked(self):
        if self.game_over:
            raise ValueError("Game over")
        if self.eliminated[self.active_player]:
            raise ValueError("Active player eliminated")
        if self.buy_prompt is not None:
            raise ValueError("Blocked: buyPrompt pending")
        if len(self.incoming_offers_for_active()) > 0:
            raise ValueError("Blocked: incoming offers pending")

    def _roll_dice(self) -> List[int]:
        d1, d2 = crypto_random.roll_dice()
        self.dice = [d1, d2]
        return self.dice

    def _move(self, player_index: int, steps: int) -> int:
        old_pos = self.player_pos[player_index]
        new_pos = (old_pos + steps) % BOARD_LEN

        # Passed START (wrap-around)
        if old_pos + steps >= BOARD_LEN:
            self.balances[player_index] += START_BONUS_FC
            self.add_message("System", f"P{player_index + 1} received {START_BONUS_FC} FC for passing START")
            self._check_bankruptcy_and_win()
            if self.game_over:
                return new_pos

        self.player_pos[player_index] = new_pos

        # Landed exactly on START (optional: if you want BOTH pass+land,
        # remove this block. Most games pay once.)
        if new_pos == START_TILE_ID and steps != 0:
            self.balances[player_index] += START_BONUS_FC
            self.add_message("System", f"P{player_index + 1} received {START_BONUS_FC} FC for landing on START")
            self._check_bankruptcy_and_win()

        return new_pos

    def _chance_news(self, player_index: int):
        # заворачиваем баланс в Wallet -> Player, применяем ChanceDeck -> возвращаем баланс обратно
        w = Wallet(self.balances[player_index])
        pl = Player(id=player_index, name=f"P{player_index+1}", pos=self.player_pos[player_index], wallet=w)

        result = self.chance_deck.apply(pl)  # {"type":"news","delta":...,"text":...}
        self.balances[player_index] = pl.wallet.balance

        self.add_message("News", result["text"], msg_type="news", delta=result["delta"])


    # ----- actions -----
    def roll(self):
        self._advance_to_next_alive()

        # If player must skip turns, consume one and pass turn
        if self.skip_turns[self.active_player] > 0:
            p = self.active_player
            self.skip_turns[p] -= 1
            self.add_message("System", f"P{p + 1} skips this turn (Prison)")
            self.next_player()
            return

        self._guard_turn_not_blocked()

        d1, d2 = self._roll_dice()
        steps = d1 + d2
        p = self.active_player

        self.add_message("Player", f"P{p+1} rolled {steps} ({d1} + {d2})")

        final_pos = self._move(p, steps)
        if final_pos == GOTO_PRISON_TILE_ID:
            self.player_pos[p] = PRISON_TILE_ID
            self.skip_turns[p] += PRISON_WAIT_TURNS
            self.add_message("System", f"P{p + 1} hit SYSTEM BUG → Prison (skip next turn)")
            self.next_player()
            return

        # prison -> skip next turn
        if final_pos == PRISON_TILE_ID:
            self.skip_turns[p] += PRISON_WAIT_TURNS
            self.add_message("System", f"P{p+1} goes to Prison and will skip the next turn")
            self.next_player()
            return


        tile = TILES_BY_ID[final_pos]

        # chance -> news
        if final_pos in CHANCE_IDS:
            self._chance_news(p)
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

        # ✅ списываем FC за покупку
        if tile.price is None:
            raise ValueError("Tile has no price")

        # price может быть float (0.12 / 0.00001), balances — int FC
        # делаем минимальную цену 1 FC, иначе мелкие цены будут 0
        cost_fc = int(tile.price)
        if tile.price > 0 and cost_fc <= 0:
            cost_fc = 1

        if self.balances[p] < cost_fc:
            # недостаточно средств: закрываем buyPrompt и идём дальше
            self.add_message("System", f"P{p+1} can't buy {tile.name}: not enough FC ({cost_fc} FC needed)")
            self.buy_prompt = None
            self.next_player()
            return

        self.balances[p] -= cost_fc
        self._check_bankruptcy_and_win()
        if self.game_over:
            self.buy_prompt = None
            return

        self.ownership[prompt_tile] = p
        self.add_message("System", f"P{p+1} bought {tile.name} for {cost_fc} FC")
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
            raise ValueError(f"Deal failed: P{buyer + 1} has not enough FC")

        # transfer FC
        self.balances[buyer] -= offer.price_fc
        self.balances[seller] += offer.price_fc

        # bankruptcy / win check
        self._check_bankruptcy_and_win()
        if self.game_over:
            self._remove_offer(offer_id)
            return

        # transfer tile ownership
        self.ownership[offer.tile_id] = buyer

        self.add_message("System", f"Deal: {tile.name} P{seller + 1} → P{buyer + 1} for {offer.price_fc} FC")

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
            "messages": [{"user": m.user, "text": m.text, "type": m.type, "delta": m.delta} for m in self.messages],
            "eliminated": self.eliminated,
            "gameOver": self.game_over,
            "winner": self.winner,
            "skipTurns": self.skip_turns
        }

