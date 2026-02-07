from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Literal, Optional

from state import GAME, snapshot


app = FastAPI(title="FlarePoly Backend", version="0.1")

# CORS (под Vite обычно нужно)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # в проде ограничь
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class OfferCreateBody(BaseModel):
    type: Literal["sell", "buy"]
    to: int = Field(..., ge=0, le=3)
    tileId: int = Field(..., ge=0, le=23)
    priceFC: int = Field(..., ge=1)


class ChatBody(BaseModel):
    text: str


class BuyBody(BaseModel):
    tileId: Optional[int] = Field(None, ge=0, le=23)


@app.get("/state")
def get_state():
    return snapshot()


@app.post("/reset")
def reset():
    GAME.reset()
    return snapshot()


@app.post("/roll")
def roll():
    # Roll: backend сам решает, можно ли ходить (если висит buyPrompt или входящие офферы)
    GAME.roll()
    return snapshot()


@app.post("/buy")
def buy(body: BuyBody):
    GAME.buy(tile_id=body.tileId)
    return snapshot()


@app.post("/skip_buy")
def skip_buy():
    GAME.skip_buy()
    return snapshot()


@app.post("/offers")
def create_offer(body: OfferCreateBody):
    GAME.create_offer(
        offer_type=body.type,
        to_player=body.to,
        tile_id=body.tileId,
        price_fc=body.priceFC,
    )
    return snapshot()


@app.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: str):
    GAME.accept_offer(offer_id)
    return snapshot()


@app.post("/offers/{offer_id}/decline")
def decline_offer(offer_id: str):
    GAME.decline_offer(offer_id)
    return snapshot()

@app.post("/chat")
def send_chat(body: ChatBody):
    # Добавляем сообщение от имени ТЕКУЩЕГО активного игрока
    p_idx = GAME.active_player
    GAME.add_message(f"P{p_idx + 1}", body.text)
    return snapshot()