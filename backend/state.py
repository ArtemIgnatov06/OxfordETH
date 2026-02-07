# state.py
from game import GameState

GAME = GameState()

def snapshot():
    return GAME.to_front()
