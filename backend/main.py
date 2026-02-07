from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional

from state import GAME, snapshot
from auth_sig import SigProof, build_action_message


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


# ---------- ENDPOINTS ----------

@app.get("/")
def health_check():
    return {"status": "online"}

@app.get("/state")
def get_state():
    return snapshot()

@app.get("/action_message")
def action_message(playerIndex: int, action: str, params: str = ""):
    """
    Frontend calls this to get the EXACT message to sign for the next action.
    Nonce is taken from GAME.nonces[playerIndex] + 1.
    """
    nonce = GAME.nonces[playerIndex] + 1
    msg = build_action_message(
        game_id="local",
        chain_id=GAME.fxrp.w3.eth.chain_id if hasattr(GAME, "fxrp") else 0,  # safe if you stub during dev
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
        proof=SigProof(**body.proof.model_dump()),
        expected_message=body.expectedMessage,
    )
    return snapshot()

@app.post("/reset")
def reset():
    GAME.reset()
    return snapshot()

@app.post("/roll")
def roll(body: SignedActionBody):
    GAME.roll(SigProof(**body.proof.model_dump()))
    return snapshot()

@app.post("/buy")
def buy(body: SignedBuyBody):
    """
    Stage 1: creates pendingSettlement for a property purchase.
    Frontend then asks user to send FXRP on-chain.
    """
    GAME.buy(proof=SigProof(**body.proof.model_dump()), tile_id=body.tileId)
    return snapshot()

@app.post("/skip_buy")
def skip_buy(body: SignedActionBody):
    GAME.skip_buy(SigProof(**body.proof.model_dump()))
    return snapshot()

@app.post("/offers")
def create_offer(body: SignedOfferCreateBody):
    GAME.create_offer(
        SigProof(**body.proof.model_dump()),
        offer_type=body.type,
        to_player=body.to,
        tile_id=body.tileId,
        price_fc=body.priceFC,
    )
    return snapshot()

@app.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: str, body: SignedActionBody):
    GAME.accept_offer(SigProof(**body.proof.model_dump()), offer_id)
    return snapshot()

@app.post("/offers/{offer_id}/decline")
def decline_offer(offer_id: str, body: SignedActionBody):
    GAME.decline_offer(SigProof(**body.proof.model_dump()), offer_id)
    return snapshot()

@app.post("/settle")
def settle(body: SignedSettleBody):
    """
    Stage 2: verify the on-chain FXRP transfer and finalize the buy/trade.
    """
    GAME.settle(SigProof(**body.proof.model_dump()), tx_hash=body.txHash)
    return snapshot()

@app.get("/player/{address}/balance")
def get_balance(address: str):
    # IMPORTANT: match your actual chain_fxrp import path
    from chain.chain_fxrp import fxrp_client
    bal = fxrp_client.get_balance(address)
    return {"address": address, "balance": bal}
