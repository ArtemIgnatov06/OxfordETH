from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
import time
import uuid
import random
import os

import crypto_random
from board import BOARD_LEN, TILES_BY_ID, BUYABLE_PROPERTY_IDS, CHANCE_IDS
from auth_sig import SigProof, build_action_message, verify_proof
from chain_fxrp import FxrpChain, PriceOracle


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
    price_fxrp_raw: int
    created_at: int

    def to_front(self):
        return {
            "id": self.id,
            "type": self.type,
            "from": self.from_player,
            "to": self.to_player,
            "tileId": self.tile_id,
            "priceFXRP": self.price_fxrp_raw,
            "createdAt": self.created_at,
        }


@dataclass
class GameState:
    players_count: int = 4
    dice: List[int] = field(default_factory=lambda: [1, 1])
    player_pos: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    active_player: int = 0

    ownership: Dict[int, int] = field(default_factory=dict)
    buy_prompt: Optional[Dict] = None

    # --- Real wallet mapping ---
    player_wallets: List[Optional[str]] = field(default_factory=lambda: [None, None, None, None])

    # anti-replay for signatures
    nonces: List[int] = field(default_factory=lambda: [0, 0, 0, 0])

    # trade offers
    trade_offers: List[TradeOffer] = field(default_factory=list)

    # settlement blocking (buy/trade waits for an ERC20 transfer)
    pending_settlement: Optional[Dict] = None
    # shape:
    # { "kind": "buy"|"trade", "from": addr, "to": addr, "amountRaw": int, "tileId": int, "offerId": str|None }

    messages: List[Message] = field(default_factory=lambda: [Message("System", "Welcome to FlarePoly Testnet!")])

    # chain
    fxrp: FxrpChain = field(default_factory=FxrpChain.from_env)
    oracle: PriceOracle = field(default_factory=PriceOracle)

    def reset(self):
        self.dice = [1, 1]
        self.player_pos = [0] * self.players_count
        self.active_player = 0
        self.ownership = {}
        self.buy_prompt = None
        self.player_wallets = [None] * self.players_count
        self.nonces = [0] * self.players_count
        self.trade_offers = []
        self.pending_settlement = None
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
        if self.pending_settlement is not None:
            raise ValueError("Blocked: pending on-chain settlement")

    def _roll_dice(self) -> List[int]:
        d1, d2 = crypto_random.roll_dice()
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

    # ----- wallet connect -----
    def connect_wallet(self, player_index: int, proof: SigProof, expected_message: str):
        if player_index < 0 or player_index >= self.players_count:
            raise ValueError("Invalid player index")

        # Message must match what backend provided (prevents signing random text)
        if proof.message != expected_message:
            raise ValueError("Message mismatch")
        if not verify_proof(proof):
            raise ValueError("Invalid signature")

        self.player_wallets[player_index] = proof.address
        self.add_message("System", f"P{player_index+1} connected wallet {proof.address}")

    # ----- signature guard for actions -----
    def _require_sig(self, action: str, params: str, proof: SigProof):
        p = self.active_player
        addr = self.player_wallets[p]
        if not addr:
            raise ValueError("Active player has no connected wallet")
        if proof.address.lower() != addr.lower():
            raise ValueError("Signature wallet != connected wallet")

        expected = build_action_message(
            game_id=os.getenv("GAME_ID", "local"),
            chain_id=self.fxrp.w3.eth.chain_id,
            player_index=p,
            action=action,
            params=params,
            nonce=self.nonces[p] + 1,
        )
        if proof.message != expected:
            raise ValueError("Bad signed message (nonce/params mismatch)")
        if not verify_proof(proof):
            raise ValueError("Invalid signature")

        # consume nonce
        self.nonces[p] += 1

    # ----- economics: USD tile -> FXRP amount -----
    def _usd_to_fxrp_raw(self, usd: float) -> int:
        # If oracle is configured later: use oracle.fxrp_usd()
        price = self.oracle.fxrp_usd()
        fxrp_per_usd = 1.0 if price is None else (1.0 / price)

        fxrp_amount = usd * fxrp_per_usd
        decimals = self.fxrp.decimals()
        return int(round(fxrp_amount * (10 ** decimals)))

    # ----- actions -----
    def roll(self, proof: SigProof):
        self._guard_turn_not_blocked()
        self._require_sig("ROLL", "", proof)

        d1, d2 = self._roll_dice()
        steps = d1 + d2
        p = self.active_player

        self.add_message("Player", f"P{p+1} rolled {steps} ({d1} + {d2})")
        final_pos = self._move(p, steps)
        tile = TILES_BY_ID[final_pos]

        if final_pos in CHANCE_IDS:
            self._chance_news()
            self.next_player()
            return

        if final_pos in BUYABLE_PROPERTY_IDS and final_pos not in self.ownership:
            self.buy_prompt = {"tileId": final_pos, "playerIndex": p}
            return

        self.next_player()

    def buy(self, proof: SigProof, tile_id: Optional[int] = None):
        if self.buy_prompt is None:
            raise ValueError("No buy prompt")
        p = self.buy_prompt["playerIndex"]
        if p != self.active_player:
            raise ValueError("Not your buy prompt")

        prompt_tile = self.buy_prompt["tileId"]
        if tile_id is not None and tile_id != prompt_tile:
            raise ValueError("Tile mismatch")

        self._require_sig("BUY", f"tileId={prompt_tile}", proof)

        if prompt_tile in self.ownership:
            self.buy_prompt = None
            self.add_message("System", "Buy failed: already owned")
            self.next_player()
            return

        tile = TILES_BY_ID[prompt_tile]
        if tile.price is None:
            raise ValueError("Tile has no price")

        buyer_addr = self.player_wallets[p]
        if not buyer_addr:
            raise ValueError("Wallet not connected")

        cost_raw = self._usd_to_fxrp_raw(float(tile.price))

        # Block the game until they pay on-chain and submit tx hash
        self.pending_settlement = {
            "kind": "buy",
            "from": buyer_addr,
            "to": os.getenv("TREASURY_WALLET", buyer_addr),  # set a treasury wallet in env
            "amountRaw": cost_raw,
            "tileId": prompt_tile,
            "offerId": None,
        }

        self.add_message("System", f"Payment required: send FXRP (raw={cost_raw}) then submit tx hash via /settle")

    def skip_buy(self, proof: SigProof):
        if self.buy_prompt is None:
            raise ValueError("No buy prompt")
        p = self.buy_prompt["playerIndex"]
        self._require_sig("SKIP_BUY", f"tileId={self.buy_prompt['tileId']}", proof)

        tile = TILES_BY_ID[self.buy_prompt["tileId"]]
        self.add_message("System", f"P{p+1} skipped {tile.name}")
        self.buy_prompt = None
        self.next_player()

    # ----- offers -----
    def create_offer(self, proof: SigProof, offer_type: OfferType, to_player: int, tile_id: int, price_fxrp_raw: int):
        self._guard_turn_not_blocked()
        self._require_sig("CREATE_OFFER", f"type={offer_type}&to={to_player}&tileId={tile_id}&price={price_fxrp_raw}", proof)

        if to_player == self.active_player:
            raise ValueError("Cannot target yourself")
        if tile_id not in BUYABLE_PROPERTY_IDS:
            raise ValueError("Tile not tradable")
        if price_fxrp_raw <= 0:
            raise ValueError("Price must be > 0")

        tile = TILES_BY_ID[tile_id]
        owner = self.ownership.get(tile_id)

        if offer_type == "sell":
            if owner != self.active_player:
                raise ValueError("You can sell only your own tile")
        else:
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
            price_fxrp_raw=int(price_fxrp_raw),
            created_at=int(time.time() * 1000),
        )
        self.trade_offers.insert(0, offer)

        if offer_type == "sell":
            self.add_message("System", f"P{offer.from_player+1} offers to SELL {tile.name} to P{offer.to_player+1} for FXRP(raw={offer.price_fxrp_raw})")
        else:
            self.add_message("System", f"P{offer.from_player+1} offers to BUY {tile.name} from P{offer.to_player+1} for FXRP(raw={offer.price_fxrp_raw})")

    def _find_offer(self, offer_id: str) -> TradeOffer:
        for o in self.trade_offers:
            if o.id == offer_id:
                return o
        raise ValueError("Offer not found")

    def accept_offer(self, proof: SigProof, offer_id: str):
        offer = self._find_offer(offer_id)
        if self.active_player != offer.to_player:
            raise ValueError("Accept offers only on your turn")

        self._require_sig("ACCEPT_OFFER", f"offerId={offer_id}", proof)

        tile = TILES_BY_ID[offer.tile_id]
        current_owner = self.ownership.get(offer.tile_id)

        seller = offer.from_player if offer.type == "sell" else offer.to_player
        buyer = offer.to_player if offer.type == "sell" else offer.from_player

        if current_owner != seller:
            self._remove_offer(offer_id)
            self.add_message("System", f"Offer invalid: tile owner changed for {tile.name}")
            return

        buyer_addr = self.player_wallets[buyer]
        seller_addr = self.player_wallets[seller]
        if not buyer_addr or not seller_addr:
            raise ValueError("Both players must have connected wallets")

        # Require on-chain settlement before transferring ownership
        self.pending_settlement = {
            "kind": "trade",
            "from": buyer_addr,
            "to": seller_addr,
            "amountRaw": offer.price_fxrp_raw,
            "tileId": offer.tile_id,
            "offerId": offer_id,
        }
        self.add_message("System", f"Trade settlement required: send FXRP(raw={offer.price_fxrp_raw}) then submit tx hash via /settle")

    def decline_offer(self, proof: SigProof, offer_id: str):
        offer = self._find_offer(offer_id)
        if self.active_player != offer.to_player:
            raise ValueError("Decline offers only on your turn")
        self._require_sig("DECLINE_OFFER", f"offerId={offer_id}", proof)

        self.add_message("System", f"Offer declined by P{offer.to_player+1}")
        self._remove_offer(offer_id)
        self.next_player()

    def _remove_offer(self, offer_id: str):
        self.trade_offers = [o for o in self.trade_offers if o.id != offer_id]

    # ----- settlement -----
    def settle(self, proof: SigProof, tx_hash: str):
        if not self.pending_settlement:
            raise ValueError("No pending settlement")
        self._require_sig("SETTLE", f"tx={tx_hash}", proof)

        ps = self.pending_settlement
        ok, reason = self.fxrp.verify_erc20_transfer(
            tx_hash=tx_hash,
            expected_from=ps["from"],
            expected_to=ps["to"],
            expected_amount_raw=int(ps["amountRaw"]),
            min_confirmations=int(os.getenv("MIN_CONFIRMATIONS", "1")),
        )
        if not ok:
            raise ValueError(f"Settlement not verified: {reason}")

        tile = TILES_BY_ID[ps["tileId"]]

        if ps["kind"] == "buy":
            p = self.active_player
            self.ownership[ps["tileId"]] = p
            self.add_message("System", f"Buy settled: P{p+1} bought {tile.name} (paid on-chain)")
            self.buy_prompt = None
            self.pending_settlement = None
            self.next_player()
            return

        if ps["kind"] == "trade":
            offer_id = ps["offerId"]
            offer = self._find_offer(offer_id)
            seller = offer.from_player if offer.type == "sell" else offer.to_player
            buyer = offer.to_player if offer.type == "sell" else offer.from_player

            self.ownership[offer.tile_id] = buyer
            self.add_message("System", f"Trade settled: {tile.name} P{seller+1} → P{buyer+1} (paid on-chain)")
            self._remove_offer(offer_id)
            self.pending_settlement = None
            self.next_player()
            return

        raise ValueError("Unknown settlement kind")

    # ----- serialization -----
    def to_front(self):
        # balances = real FXRP balances (float) for each player wallet, else 0
        balances = []
        for a in self.player_wallets[: self.players_count]:
            balances.append(self.fxrp.balance_of_float(a) if a else 0.0)

        return {
            "dice": self.dice,
            "playerPos": self.player_pos,
            "activePlayer": self.active_player,
            "ownership": {str(k): v for k, v in self.ownership.items()},
            "buyPrompt": self.buy_prompt,
            "balances": balances,  # now FXRP balances (float)
            "tradeOffers": [o.to_front() for o in self.trade_offers],
            "pendingSettlement": self.pending_settlement,
            "playerWallets": self.player_wallets,
            "messages": [{"user": m.user, "text": m.text} for m in self.messages],
        }
