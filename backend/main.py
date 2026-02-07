from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional

from state import GAME, snapshot
from auth_sig import SigProof, build_action_message


app = FastAPI(title="FlarePoly Backend", version="0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProofBody(BaseModel):
    address: str
    message: str
    signature: str


class ConnectWalletBody(BaseModel):
    playerIndex: int = Field(..., ge=0, le=3)
    proof: ProofBody
    expectedMessage: str


class OfferCreateBody(BaseModel):
    type: Literal["sell", "buy"]
    to: int = Field(..., ge=0, le=3)
    tileId: int = Field(..., ge=0, le=23)
    priceFXRP: int = Field(..., ge=1)  # raw units


class BuyBody(BaseModel):
    tileId: Optional[int] = Field(None, ge=0, le=23)


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
    priceFXRP: int = Field(..., ge=1)


class SignedSettleBody(BaseModel):
    proof: ProofBody
    txHash: str


@app.get("/state")
def get_state():
    return snapshot()


@app.get("/action_message")
def action_message(playerIndex: int, action: str, params: str = ""):
    """
    Frontend calls this to get the EXACT message to sign for the next action.
    Uses current nonce+1 from GAME.
    """
    nonce = GAME.nonces[playerIndex] + 1
    msg = build_action_message(
        game_id="local",
        chain_id=GAME.fxrp.w3.eth.chain_id,
        player_index=playerIndex,
        action=action,
        params=params,
        nonce=nonce,
    )
    return {"message": msg, "nonce": nonce}


@app.post("/connect_wallet")
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
    GAME.buy(SigProof(**body.proof.model_dump()), tile_id=body.tileId)
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
        price_fxrp_raw=body.priceFXRP,
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
    GAME.settle(SigProof(**body.proof.model_dump()), tx_hash=body.txHash)
    return snapshot()
