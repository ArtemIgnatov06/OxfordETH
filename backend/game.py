from dataclasses import dataclass, field
from typing import Dict, List, Optional, Literal
import time
import uuid
import os

import crypto_random
from board import BOARD_LEN, TILES_BY_ID, BUYABLE_PROPERTY_IDS, CHANCE_IDS
from chance import ChanceDeck
from wallet import Wallet as FcWallet
from player import Player

from auth_sig import SigProof, build_action_message, verify_proof
from chain.chain_fxrp import fxrp_client  # <-- use your real on-chain client :contentReference[oaicite:3]{index=3}

from web3 import Web3
from web3._utils.events import get_event_data
from hexbytes import HexBytes


OfferType = Literal["sell", "buy"]

START_TILE_ID = 0
START_BONUS_FC = 200
PRISON_WAIT_TURNS = 1
PRISON_TILE_ID = 6
GOTO_PRISON_TILE_ID = 18


# GameFXRP is almost certainly 18 decimals (wei-style). Keep it explicit.
FXRP_DECIMALS = int(os.getenv("FXRP_DECIMALS", "18"))


def _require_sig_enabled() -> bool:
    return os.getenv("REQUIRE_SIG", "1").strip() not in ("0", "false", "False")


def _to_checksum(a: str) -> str:
    return Web3.to_checksum_address(a)


@dataclass
class Message:
    user: str
    text: str
    type: str = "chat"
    delta: Optional[int] = None


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
    players_count: int = 3

    dice: List[int] = field(default_factory=lambda: [1, 1])
    player_pos: List[int] = field(default_factory=lambda: [0, 0, 0, 0])
    active_player: int = 0

    eliminated: List[bool] = field(default_factory=lambda: [False, False, False, False])
    game_over: bool = False
    winner: Optional[int] = None
    chance_deck: ChanceDeck = field(default_factory=ChanceDeck)
    skip_turns: List[int] = field(default_factory=lambda: [0, 0, 0, 0])

    ownership: Dict[int, int] = field(default_factory=dict)
    buy_prompt: Optional[Dict] = None

    # In-game FC (for bankruptcy/winner logic)
    balances: List[int] = field(default_factory=lambda: [4200, 1337, 777, 9001])

    trade_offers: List[TradeOffer] = field(default_factory=list)

    messages: List[Message] = field(default_factory=lambda: [Message("System", "Welcome to FlarePoly Testnet!", "system")])

    # Wallet mapping + signature nonces
    player_wallets: List[Optional[str]] = field(default_factory=lambda: [None, None, None, None])
    nonces: List[int] = field(default_factory=lambda: [0, 0, 0, 0])

    # Pending settlement: we require an on-chain FXRP transfer before finalizing buy/trade
    pending_settlement: Optional[Dict] = None
    # {"kind":"buy"|"trade","from":addr,"to":addr,"amountRaw":int,"tileId":int,"offerId":str|None}

    def reset(self):
        self.dice = [1, 1]
        self.player_pos = [0] * self.players_count
        self.active_player = 0

        self.ownership = {}
        self.buy_prompt = None

        self.balances = [4200, 1337, 777, 9001][: self.players_count]
        self.trade_offers = []
        self.messages = [Message("System", "Welcome to FlarePoly Testnet!", "system")]

        self.eliminated = [False] * self.players_count
        self.game_over = False
        self.winner = None
        self.skip_turns = [0] * self.players_count

        self.player_wallets = [None] * self.players_count
        self.nonces = [0] * self.players_count
        self.pending_settlement = None

    # ---------------- helpers ----------------
    def chat(self, text: str, proof: Optional[SigProof] = None):
        text = (text or "").strip()
        if not text:
            return

        # CHAT подписываем так же, как остальные actions
        self._require_sig("CHAT", f"text={text}", proof)

        p = self.active_player
        self.add_message(f"P{p+1}", text, "chat")

    def add_message(self, user: str, text: str, msg_type: str = "chat", delta: Optional[int] = None):
        self.messages.append(Message(user, text, msg_type, delta))

    def _alive_players(self) -> List[int]:
        return [i for i in range(self.players_count) if not self.eliminated[i]]

    def _advance_to_next_alive(self):
        for _ in range(self.players_count):
            if not self.eliminated[self.active_player]:
                return
            self.active_player = (self.active_player + 1) % self.players_count

    def _check_bankruptcy_and_win(self):
        for i in range(self.players_count):
            if not self.eliminated[i] and self.balances[i] <= 0:
                self.eliminated[i] = True
                self.add_message("System", f"P{i+1} is BANKRUPT and out of the game", "system")

        alive = self._alive_players()
        if len(alive) == 1:
            self.game_over = True
            self.winner = alive[0]
            self.add_message("System", f"P{self.winner+1} wins! 🎉", "system")
            self.buy_prompt = None
            self.trade_offers = []
            self.pending_settlement = None
            return

        if self.eliminated[self.active_player] and len(alive) > 0:
            self._advance_to_next_alive()

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
        if self.pending_settlement is not None:
            raise ValueError("Blocked: pending on-chain settlement")

    def _roll_dice(self) -> List[int]:
        d1, d2 = crypto_random.roll_dice()
        self.dice = [d1, d2]
        return self.dice

    def _move(self, player_index: int, steps: int) -> int:
        old_pos = self.player_pos[player_index]
        new_pos = (old_pos + steps) % BOARD_LEN

        # pass START
        if old_pos + steps >= BOARD_LEN:
            self.balances[player_index] += START_BONUS_FC
            self.add_message("System", f"P{player_index + 1} received {START_BONUS_FC} FC for passing START", "system")
            self._check_bankruptcy_and_win()
            if self.game_over:
                return new_pos

        self.player_pos[player_index] = new_pos

        # land on START
        if new_pos == START_TILE_ID and steps != 0:
            self.balances[player_index] += START_BONUS_FC
            self.add_message("System", f"P{player_index + 1} received {START_BONUS_FC} FC for landing on START", "system")
            self._check_bankruptcy_and_win()

        return new_pos

    def _chance_news(self, player_index: int):
        w = FcWallet(self.balances[player_index])
        pl = Player(id=player_index, name=f"P{player_index+1}", pos=self.player_pos[player_index], wallet=w)

        result = self.chance_deck.apply(pl)
        self.balances[player_index] = pl.wallet.balance

        self.add_message("News", result["text"], msg_type="news", delta=result.get("delta"))
        self._check_bankruptcy_and_win()

    # ---------------- wallet connect + signatures ----------------



    def connect_wallet(self, player_index: int, proof: SigProof, expected_message: str):
        if player_index < 0 or player_index >= self.players_count:
            raise ValueError("Invalid player index")
        if proof.message != expected_message:
            raise ValueError("Message mismatch")
        if not verify_proof(proof):
            raise ValueError("Invalid signature")

        self.player_wallets[player_index] = proof.address
        self.add_message("System", f"P{player_index+1} connected wallet {proof.address}", "system")

    def _require_sig(self, action: str, params: str, proof: Optional[SigProof]):
        if not _require_sig_enabled():
            return

        if proof is None:
            raise ValueError("Missing signature proof")

        p = self.active_player
        addr = self.player_wallets[p]
        if not addr:
            raise ValueError("Active player has no connected wallet")
        if proof.address.lower() != addr.lower():
            raise ValueError("Signature wallet != connected wallet")

        expected = build_action_message(
            game_id=os.getenv("GAME_ID", "local"),
            chain_id=fxrp_client.get_chain_id(),
            player_index=p,
            action=action,
            params=params,
            nonce=self.nonces[p] + 1,
        )
        if proof.message != expected:
            raise ValueError("Bad signed message (nonce/params mismatch)")
        if not verify_proof(proof):
            raise ValueError("Invalid signature")

        self.nonces[p] += 1

    # ---------------- economics (keep deterministic + simple) ----------------

    def _usd_to_fxrp_raw(self, usd: float) -> int:
        # For now: 1 USD == 1 FXRP (until you wire FTSO price feed)
        fxrp_amount = float(usd)
        return int(round(fxrp_amount * (10 ** FXRP_DECIMALS)))

    def _fc_to_fxrp_raw(self, fc: int) -> int:
        # 1 FC == $1 (simple mapping)
        return self._usd_to_fxrp_raw(float(fc))

    # ---------------- settlement verification (on-chain) ----------------

    def _verify_fxrp_transfer(self, *, tx_hash: str, expected_from: str, expected_to: str,
                              expected_amount_raw: int) -> None:
        w3 = fxrp_client.w3
        receipt = w3.eth.get_transaction_receipt(tx_hash)
        if receipt is None:
            raise ValueError("tx not found / not mined")
        if receipt.get("status") != 1:
            raise ValueError("tx failed")

        # confirmations
        min_conf = int(os.getenv("MIN_CONFIRMATIONS", "1"))
        latest = w3.eth.block_number
        conf = latest - receipt["blockNumber"] + 1
        if conf < min_conf:
            raise ValueError(f"not enough confirmations ({conf}/{min_conf})")

        contract = fxrp_client.contract
        fxrp_addr = Web3.to_checksum_address(contract.address)

        # Transfer topic0
        transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)")  # bytes32
        event_abi = contract.events.Transfer._get_event_abi()

        for log in receipt["logs"]:
            if Web3.to_checksum_address(log["address"]) != fxrp_addr:
                continue

            topics = log.get("topics", [])
            if not topics:
                continue

            if HexBytes(topics[0]) != HexBytes(transfer_topic):
                continue

            decoded = get_event_data(w3.codec, event_abi, log)

        ef = Web3.to_checksum_address(expected_from)
        et = Web3.to_checksum_address(expected_to)
        ev_amt = int(expected_amount_raw)

        # Decode only relevant logs -> no MismatchedABI spam


        for log in receipt["logs"]:
            if Web3.to_checksum_address(log["address"]) != fxrp_addr:
                continue
            if not log["topics"] or log["topics"][0].hex() != transfer_topic:
                continue

            decoded = get_event_data(w3.codec, event_abi, log)
            args = decoded["args"]

            if (Web3.to_checksum_address(args["from"]) == ef and
                    Web3.to_checksum_address(args["to"]) == et and
                    int(args["value"]) == ev_amt):
                return

        raise ValueError("no matching FXRP Transfer found in tx")

    # ---------------- actions ----------------

    def roll(self, proof: Optional[SigProof] = None):
        self._advance_to_next_alive()

        # prison skip
        if self.skip_turns[self.active_player] > 0:
            p = self.active_player
            self.skip_turns[p] -= 1
            self._require_sig("SKIP_TURN", "reason=prison", proof)
            self.add_message("System", f"P{p + 1} skips this turn (Prison)", "system")
            self.next_player()
            return

        self._guard_turn_not_blocked()
        self._require_sig("ROLL", "", proof)

        d1, d2 = self._roll_dice()
        steps = d1 + d2
        p = self.active_player

        self.add_message("Player", f"P{p+1} rolled {steps} ({d1} + {d2})", "chat")

        final_pos = self._move(p, steps)

        if final_pos == GOTO_PRISON_TILE_ID:
            self.player_pos[p] = PRISON_TILE_ID
            self.skip_turns[p] += PRISON_WAIT_TURNS
            self.add_message("System", f"P{p + 1} hit SYSTEM BUG → Prison (skip next turn)", "system")
            self.next_player()
            return

        if final_pos == PRISON_TILE_ID:
            self.skip_turns[p] += PRISON_WAIT_TURNS
            self.add_message("System", f"P{p+1} goes to Prison and will skip the next turn", "system")
            self.next_player()
            return

        if final_pos in CHANCE_IDS:
            self._chance_news(p)
            if not self.game_over:
                self.next_player()
            return

        if final_pos in BUYABLE_PROPERTY_IDS and final_pos not in self.ownership:
            self.buy_prompt = {"tileId": final_pos, "playerIndex": p}
            return

        self.next_player()

    def buy(self, proof: Optional[SigProof] = None, tile_id: Optional[int] = None):
        if self.buy_prompt is None:
            raise ValueError("No buy prompt")

        prompt_tile = self.buy_prompt["tileId"]
        p = self.buy_prompt["playerIndex"]

        if p != self.active_player:
            raise ValueError("Not your buy prompt")
        if tile_id is not None and tile_id != prompt_tile:
            raise ValueError("Tile mismatch")

        self._require_sig("BUY", f"tileId={prompt_tile}", proof)

        if prompt_tile in self.ownership:
            self.buy_prompt = None
            self.add_message("System", "Buy failed: already owned", "system")
            self.next_player()
            return

        tile = TILES_BY_ID[prompt_tile]
        if tile.price is None:
            raise ValueError("Tile has no price")

        buyer_addr = self.player_wallets[p]
        if _require_sig_enabled() and not buyer_addr:
            raise ValueError("Wallet not connected")

        cost_raw = self._usd_to_fxrp_raw(float(tile.price))

        to_addr = os.getenv("TREASURY_WALLET", buyer_addr or "0x0000000000000000000000000000000000000000")
        self.pending_settlement = {
            "kind": "buy",
            "from": buyer_addr,
            "to": to_addr,
            "amountRaw": cost_raw,
            "tileId": prompt_tile,
            "offerId": None,
        }

        self.add_message("System", f"Payment required: send FXRP(raw={cost_raw}) then submit tx hash via /settle", "system")

    def skip_buy(self, proof: Optional[SigProof] = None):
        if self.buy_prompt is None:
            raise ValueError("No buy prompt")

        self._require_sig("SKIP_BUY", f"tileId={self.buy_prompt['tileId']}", proof)

        p = self.buy_prompt["playerIndex"]
        tile = TILES_BY_ID[self.buy_prompt["tileId"]]
        self.add_message("System", f"P{p+1} skipped {tile.name}", "system")
        self.buy_prompt = None
        self.next_player()

    def create_offer(self, proof: Optional[SigProof], offer_type: OfferType, to_player: int, tile_id: int, price_fc: int):
        self._guard_turn_not_blocked()
        self._require_sig("CREATE_OFFER", f"type={offer_type}&to={to_player}&tileId={tile_id}&priceFC={price_fc}", proof)

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
        else:
            if owner is None:
                raise ValueError("Tile not owned")
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
            self.add_message("System", f"P{offer.from_player+1} offers to SELL {tile.name} to P{offer.to_player+1} for {offer.price_fc} FC", "system")
        else:
            self.add_message("System", f"P{offer.from_player+1} offers to BUY {tile.name} from P{offer.to_player+1} for {offer.price_fc} FC", "system")

    def _find_offer(self, offer_id: str) -> TradeOffer:
        for o in self.trade_offers:
            if o.id == offer_id:
                return o
        raise ValueError("Offer not found")

    def _remove_offer(self, offer_id: str):
        self.trade_offers = [o for o in self.trade_offers if o.id != offer_id]

    def accept_offer(self, proof: Optional[SigProof], offer_id: str):
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
            self.add_message("System", f"Offer invalid: tile owner changed for {tile.name}", "system")
            return

        if self.balances[buyer] < offer.price_fc:
            raise ValueError(f"Deal failed: P{buyer + 1} has not enough FC")

        buyer_addr = self.player_wallets[buyer]
        seller_addr = self.player_wallets[seller]
        if _require_sig_enabled() and (not buyer_addr or not seller_addr):
            raise ValueError("Both players must have connected wallets")

        amount_raw = self._fc_to_fxrp_raw(offer.price_fc)
        self.pending_settlement = {
            "kind": "trade",
            "from": buyer_addr,
            "to": seller_addr,
            "amountRaw": amount_raw,
            "tileId": offer.tile_id,
            "offerId": offer_id,
        }
        self.add_message("System", f"Trade settlement required: send FXRP(raw={amount_raw}) then submit tx hash via /settle", "system")

    def decline_offer(self, proof: Optional[SigProof], offer_id: str):
        offer = self._find_offer(offer_id)
        if self.active_player != offer.to_player:
            raise ValueError("Decline offers only on your turn")

        self._require_sig("DECLINE_OFFER", f"offerId={offer_id}", proof)

        self.add_message("System", f"Offer declined by P{offer.to_player+1}", "system")
        self._remove_offer(offer_id)
        self.next_player()

    def settle(self, proof: Optional[SigProof], tx_hash: str):
        if not self.pending_settlement:
            raise ValueError("No pending settlement")

        self._require_sig("SETTLE", f"tx={tx_hash}", proof)

        ps = self.pending_settlement
        self._verify_fxrp_transfer(
            tx_hash=tx_hash,
            expected_from=ps["from"],
            expected_to=ps["to"],
            expected_amount_raw=int(ps["amountRaw"]),
        )

        tile = TILES_BY_ID[ps["tileId"]]

        if ps["kind"] == "buy":
            p = self.active_player
            self.ownership[ps["tileId"]] = p
            self.add_message("System", f"Buy settled: P{p+1} bought {tile.name} (paid on-chain)", "system")
            self.buy_prompt = None
            self.pending_settlement = None
            self.next_player()
            return

        if ps["kind"] == "trade":
            offer_id = ps["offerId"]
            offer = self._find_offer(offer_id)

            seller = offer.from_player if offer.type == "sell" else offer.to_player
            buyer = offer.to_player if offer.type == "sell" else offer.from_player

            # Apply FC transfer after on-chain proof
            self.balances[buyer] -= offer.price_fc
            self.balances[seller] += offer.price_fc
            self._check_bankruptcy_and_win()
            if self.game_over:
                self._remove_offer(offer_id)
                self.pending_settlement = None
                return

            self.ownership[offer.tile_id] = buyer
            self.add_message("System", f"Trade settled: {tile.name} P{seller+1} → P{buyer+1} (paid on-chain)", "system")
            self._remove_offer(offer_id)
            self.pending_settlement = None
            self.next_player()
            return

        raise ValueError("Unknown settlement kind")

    # ---------------- serialization ----------------

    def to_front(self):
        # On-chain FXRP balances via your chain_fxrp client
        balances_fxrp = []
        for a in self.player_wallets[: self.players_count]:
            balances_fxrp.append(fxrp_client.get_balance(a) if a else 0.0)

        return {
            "dice": self.dice,
            "playerPos": self.player_pos,
            "activePlayer": self.active_player,
            "ownership": {str(k): v for k, v in self.ownership.items()},
            "buyPrompt": self.buy_prompt,

            # Gameplay currency
            "balances": self.balances,

            # Real on-chain balance for UI
            "balancesFXRP": balances_fxrp,
            "playerWallets": self.player_wallets,
            "pendingSettlement": self.pending_settlement,

            "tradeOffers": [o.to_front() for o in self.trade_offers],
            "messages": [{"user": m.user, "text": m.text, "type": m.type, "delta": m.delta} for m in self.messages],

            "eliminated": self.eliminated,
            "gameOver": self.game_over,
            "winner": self.winner,
            "skipTurns": self.skip_turns,
        }

