from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

from Board import BoardGame, Player

app = FastAPI(title="CryptoMonopoly Backend (Prototype)")


# ---- In-memory singleton game ----
ENGINE = BoardGame(
    players=[Player("P1"), Player("P2"), Player("P3")],
    seed=7,
)


class ActionRequest(BaseModel):
    type: str
    propertyId: Optional[str] = None


@app.get("/game/state")
def get_state():
    return ENGINE.state()


@app.get("/game/layout")
def get_layout():
    """Static board definition (24 tiles, ids 0..23)."""
    return {"tiles": ENGINE.layout}


@app.post("/game/roll")
def roll():
    try:
        return ENGINE.roll_and_move()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/game/end-turn")
def end_turn():
    return ENGINE.end_turn()


@app.post("/game/action")
def action(req: ActionRequest):
    try:
        return ENGINE.perform_action(req.type, req.propertyId)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
