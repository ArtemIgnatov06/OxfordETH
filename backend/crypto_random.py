import time
import json
import os
from web3 import Web3

# --- Configuration (DO NOT hardcode secrets) ---
RPC_URL = os.getenv("FLARE_RPC_URL", "https://coston2-api.flare.network/ext/C/rpc")
CONTRACT_ADDRESS = os.getenv("DICE_CONTRACT_ADDRESS", "").strip()
PRIVATE_KEY = os.getenv("DICE_PRIVATE_KEY", "").strip()
WALLET_ADDRESS = os.getenv("DICE_WALLET_ADDRESS", "").strip()

w3 = Web3(Web3.HTTPProvider(RPC_URL))

# Load ABI relative to this file (robust in Docker)
ABI_PATH = os.getenv("DICE_ABI_PATH", "SecureDiceRoller.json")
with open(ABI_PATH, "r") as f:
    contract_abi = json.load(f)["abi"]

if not CONTRACT_ADDRESS:
    raise RuntimeError("Missing DICE_CONTRACT_ADDRESS env var")
contract = w3.eth.contract(address=Web3.to_checksum_address(CONTRACT_ADDRESS), abi=contract_abi)

def roll_dice():
    """
    Returns (die1, die2) or raises an exception.
    Never prints, never runs on import.
    """
    if not PRIVATE_KEY or not WALLET_ADDRESS:
        raise RuntimeError("Missing DICE_PRIVATE_KEY / DICE_WALLET_ADDRESS env vars")

    # Retry loop (handles 'not secure' case)
    while True:
        nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)

        tx = contract.functions.rollDice().build_transaction({
            "from": WALLET_ADDRESS,
            "nonce": nonce,
            "gas": 250000,
            "gasPrice": w3.eth.gas_price,
            "chainId": 114,   # Coston2
        })

        signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        receipt = w3.eth.wait_for_transaction_receipt(tx_hash)

        try:
            logs = contract.events.DiceRolled().process_receipt(receipt)
        except Exception as e:
            # If between rounds, your contract may revert or emit nothing
            if "not secure" in str(e):
                time.sleep(5)
                continue
            raise

        if not logs:
            # No event => treat as failure, retry a bit (or raise)
            time.sleep(2)
            continue

        res = logs[0]["args"]
        return int(res["die1"]), int(res["die2"])
