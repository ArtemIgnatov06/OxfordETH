from fastapi import HTTPException
from game import GameState

GAME = GameState(players_count=4)

def snapshot():
    return GAME.to_front()

def _wrap(fn):
    try:
        fn()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# convenience wrappers if you want to keep main.py clean:
def safe_roll():
    _wrap(GAME.roll)

def safe_buy(tile_id=None):
    _wrap(lambda: GAME.buy(tile_id))

def safe_skip_buy():
    _wrap(GAME.skip_buy)

def safe_create_offer(*args, **kwargs):
    _wrap(lambda: GAME.create_offer(*args, **kwargs))

def safe_accept_offer(offer_id: str):
    _wrap(lambda: GAME.accept_offer(offer_id))

def safe_decline_offer(offer_id: str):
    _wrap(lambda: GAME.decline_offer(offer_id))
