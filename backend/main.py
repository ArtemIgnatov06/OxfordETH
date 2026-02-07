from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Literal

from models import Player, Wallet, Board, Cell, Street, NewsCell, StartCell, ChanceDeck, TradeOffer
from game import Game
from storage import save_state
import random

app = FastAPI()

# ---- Create initial game (edit prices/ids to match your map)
def make_game() -> Game:
    players = [
        Player(0, "P1", 0, Wallet(4200)),
        Player(1, "P2", 0, Wallet(1337)),
        Player(2, "P3", 0, Wallet(777)),
        Player(3, "P4", 0, Wallet(9001)),
    ]

    cells = [Cell(i, f"Cell {i}") for i in range(24)]
    cells[0] = StartCell(0, "Start")
    for nid in [3, 9, 16, 22]:
        cells[nid] = NewsCell(nid, "News")

    street_ids = [1,2,4,5,6,7,8,10,11,12,13,14,15,17]  # 14 streets
    price = 200
    for sid in street_ids:
        cells[sid] = Street(sid, f"Street {sid}", price)
        price += 50

    board = Board(cells)
    chance = ChanceDeck()
    return Game(players, board, chance)

game = make_game()
save_state(game.to_state())

# ---- API DTOs
class RollReq(BaseModel):
    playerId: int

class OfferReq(BaseModel):
    type: Literal["sell", "buy"]
    fromPlayer: int
    toPlayer: int
    cellId: int
    price: int = Field(gt=0)

class AcceptReq(BaseModel):
    playerId: int

@app.get("/state")
def get_state():
    return game.to_state()

@app.post("/reset")
def reset():
    global game
    game = make_game()
    save_state(game.to_state())
    return game.to_state()

@app.post("/roll")
def roll(req: RollReq):
    try:
        result = game.roll_and_move(req.playerId)
        st = game.to_state()
        save_state(st)
        return {"result": result, "state": st}
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@app.post("/buy")
def buy(req: RollReq):
    try:
        game.buy_pending(req.playerId)
        st = game.to_state()
        save_state(st)
        return st
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@app.post("/skip")
def skip(req: RollReq):
    try:
        game.skip_pending(req.playerId)
        st = game.to_state()
        save_state(st)
        return st
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@app.post("/offers")
def create_offer(req: OfferReq):
    try:
        offer = TradeOffer(
            id=str(random.randint(10**8, 10**9 - 1)),
            type=req.type,
            from_player=req.fromPlayer,
            to_player=req.toPlayer,
            cell_id=req.cellId,
            price=req.price,
        )
        game.create_offer(offer)
        st = game.to_state()
        save_state(st)
        return st
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/offers/{offer_id}/accept")
def accept_offer(offer_id: str, req: AcceptReq):
    try:
        game.accept_offer(offer_id, req.playerId)
        st = game.to_state()
        save_state(st)
        return st
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
