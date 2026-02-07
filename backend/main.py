from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional

# Import your Game State and Auth
from backend.state import GAME, snapshot
from backend.auth_sig import SigProof, build_action_message

app = FastAPI(title="FlarePoly Backend", version="0.2")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- MODELS ---

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
    priceFXRP: int = Field(..., ge=1)

# ✅ UPDATED: Added txHash to prove payment
class SignedBuyBody(BaseModel):
    proof: ProofBody
    tileId: Optional[int] = Field(None, ge=0, le=23)
    txHash: Optional[str] = None  # <--- NEW FIELD

class SignedActionBody(BaseModel):
    proof: ProofBody

class SignedOfferCreateBody(BaseModel):
    proof: ProofBody
    type: Literal["sell", "buy"]
    to: int = Field(..., ge=0, le=3)
    tileId: int = Field(..., ge=0, le=23)
    priceFXRP: int = Field(..., ge=1)

# --- ENDPOINTS ---

@app.get("/")
def health_check():
    return {"status": "online", "network": "Coston2"}

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
    Buys a property.
    Requires 'txHash' in the body to verify on-chain payment.
    """
    GAME.buy(
        proof=SigProof(**body.proof.model_dump()), 
        tile_id=body.tileId,
        tx_hash=body.txHash  # <--- PASSING THE HASH TO GAME LOGIC
    )
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

# Helper for frontend to check balance
@app.get("/player/{address}/balance")
def get_balance(address: str):
    # Lazy import to avoid circular dependency issues if they exist
    from chain.chain_fxrp import fxrp_client
    bal = fxrp_client.get_balance(address)
    return {"address": address, "balance": bal}