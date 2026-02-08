from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional

from state import GAME, snapshot
from auth_sig import SigProof, build_action_message

# IMPORTANT: same chain client used by GameState signature checks
from chain.chain_fxrp import fxrp_client


app = FastAPI(title="FlarePoly Backend", version="0.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- MODELS ----------

class ProofBody(BaseModel):
    address: str
    message: str
    signature: str


class ConnectWalletBody(BaseModel):
    playerIndex: int = Field(..., ge=0, le=3)
    proof: ProofBody
    expectedMessage: str


class SignedActionBody(BaseModel):
    proof: ProofBody


class SignedBuyBody(BaseModel):
    proof: ProofBody
    tileId: Optional[int] = Field(None, ge=0, le=23)


class SignedOfferCreateBody(BaseModel):
    proof: ProofBody
    type: Literal["sell", "buy"]
    to: int = Field(..., ge=0, le=3)
    tileId: int = Field(..., ge=0, le=23)
    priceFC: int = Field(..., ge=1)  # keep FC for frontend mapping


class SignedSettleBody(BaseModel):
    proof: ProofBody
    txHash: str


class SignedChatBody(BaseModel):
    proof: ProofBody
    text: str


# ---------- HELPERS ----------

def _sigproof_from_body(pb: ProofBody) -> SigProof:
    # convert Pydantic model -> your SigProof
    return SigProof(**pb.model_dump())


def _current_chain_id() -> int:
    # Single source of truth for chain_id
    return int(fxrp_client.w3.eth.chain_id)


# ---------- ENDPOINTS ----------

@app.get("/")
def health_check():
    return {"status": "online"}


@app.get("/state")
def get_state():
    return snapshot()


@app.get("/chain")
def chain_info():
    # Handy for debugging MetaMask network mismatch
    cid = _current_chain_id()
    try:
        net = fxrp_client.w3.eth.get_block("latest").get("number")
    except Exception:
        net = None
    return {"chainId": cid, "latestBlock": net}


@app.get("/action_message")
def action_message(playerIndex: int, action: str, params: str = ""):
    """
    Frontend calls this to get the EXACT message to sign for the next action.
    Nonce is taken from GAME.nonces[playerIndex] + 1.

    IMPORTANT:
    chain_id must match the chain_id used inside GameState signature validation,
    otherwise you'll get "Bad signed message (nonce/params mismatch)".
    """
    nonce = GAME.nonces[playerIndex] + 1

    msg = build_action_message(
        game_id="local",
        chain_id=_current_chain_id(),
        player_index=playerIndex,
        action=action,
        params=params,
        nonce=nonce,
    )
    return {"message": msg, "nonce": nonce}


@app.post("/connect")
def connect_wallet(body: ConnectWalletBody):
    GAME.connect_wallet(
        player_index=body.playerIndex,
        proof=_sigproof_from_body(body.proof),
        expected_message=body.expectedMessage,
    )
    return snapshot()


@app.post("/reset")
def reset():
    GAME.reset()
    return snapshot()


@app.post("/chat")
def chat(body: SignedChatBody):
    GAME.chat(body.text, _sigproof_from_body(body.proof))
    return snapshot()


@app.post("/roll")
def roll(body: SignedActionBody):
    GAME.roll(_sigproof_from_body(body.proof))
    return snapshot()


@app.post("/buy")
def buy(body: SignedBuyBody):
    """
    Stage 1: creates pendingSettlement for a property purchase.
    Frontend then asks user to send FXRP on-chain.
    """
    GAME.buy(proof=_sigproof_from_body(body.proof), tile_id=body.tileId)
    return snapshot()


@app.post("/skip_buy")
def skip_buy(body: SignedActionBody):
    GAME.skip_buy(_sigproof_from_body(body.proof))
    return snapshot()


@app.post("/offers")
def create_offer(body: SignedOfferCreateBody):
    GAME.create_offer(
        _sigproof_from_body(body.proof),
        offer_type=body.type,
        to_player=body.to,
        tile_id=body.tileId,
        price_fc=body.priceFC,
    )
    return snapshot()


@app.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: str, body: SignedActionBody):
    GAME.accept_offer(_sigproof_from_body(body.proof), offer_id)
    return snapshot()


@app.post("/offers/{offer_id}/decline")
def decline_offer(offer_id: str, body: SignedActionBody):
    GAME.decline_offer(_sigproof_from_body(body.proof), offer_id)
    return snapshot()


@app.post("/settle")
def settle(body: SignedSettleBody):
    """
    Stage 2: verify the on-chain FXRP transfer and finalize the buy/trade.
    """
    GAME.settle(_sigproof_from_body(body.proof), tx_hash=body.txHash)
    return snapshot()


@app.get("/player/{address}/balance")
def get_balance(address: str):
    """
    Wallet balance (FXRP / native) for UI.
    """
    bal = fxrp_client.get_balance(address)
    return {"address": address, "balance": bal}
