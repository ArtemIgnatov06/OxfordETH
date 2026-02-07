import time
import json
from web3 import Web3

# --- Configuration ---
RPC_URL = "https://coston2-api.flare.network/ext/C/rpc"
CONTRACT_ADDRESS = "0x9a9d81b42Fa28E5C8d73273Abb53650cF4E58873"
PRIVATE_KEY = "95ffb6e01235ec644af8ee1e5340cce9f105588771f84fcb37736cbb8052b67f"
WALLET_ADDRESS = "0xB33Eb1F350fBf4Bb204EAD57A0078F573e18cD45"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
with open("dice-roller/SecureDiceRoller.json", "r") as f:
    contract_abi = json.load(f)["abi"]
contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=contract_abi)

def roll_dice():
    print("🎲 Preparing to roll...")
    
    while True:
        try:
            # Check gas and nonce
            nonce = w3.eth.get_transaction_count(WALLET_ADDRESS)
            
            # Build transaction
            tx = contract.functions.rollDice().build_transaction({
                'from': WALLET_ADDRESS,
                'nonce': nonce,
                'gas': 250000,
                'gasPrice': w3.eth.gas_price,
                'chainId': 114
            })

            # Sign and Send
            signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
            tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
            print(f"🚀 Transaction sent! Hash: {w3.to_hex(tx_hash)}")

            # Wait for receipt
            receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
            
            # Parse Events
            logs = contract.events.DiceRolled().process_receipt(receipt)
            res = logs[0]['args']
            print(f"✅ SUCCESS! Request #{res['requestId']}")
            print(f"🎰 RESULT: Die1: {res['die1']} | Die2: {res['die2']} | Total: {res['total']}")
            return res

        except Exception as e:
            if "not secure" in str(e):
                print("⏳ Flare is between rounds. Waiting 20 seconds...")
                time.sleep(20)
            else:
                print(f"❌ Error: {e}")
                break

if __name__ == "__main__":
    roll_dice()