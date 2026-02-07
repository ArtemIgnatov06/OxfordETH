import json
from typing import Dict, Any

STATE_FILE = "game_state.json"

def save_state(state: Dict[str, Any]) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
