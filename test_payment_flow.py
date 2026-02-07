import os
import requests
import json
from web3 import Web3
from eth_account import Account
from eth_account.messages import encode_defunct
from dotenv import load_dotenv

# Load config
load_dotenv()

# --- CONFIG ---
API_URL = "http://127.0.0.1:8000"
RPC_URL = os.getenv("FLARE_RPC_URL", "https://coston2-api.flare.network/ext/C/rpc")
PRIVATE_KEY = os.getenv("PRIVATE_KEY")
FXRP_CONTRACT = os.getenv("FXRP_CONTRACT")
TREASURY_ADDRESS = "0x000000000000000000000000000000000000dEaD" # Burn address for testing, or use another wallet
ITEM_COST = 10 # FXRP

if not PRIVATE_KEY or not FXRP_CONTRACT:
    raise ValueError("❌ Check your .env file! Missing PRIVATE_KEY or FXRP_CONTRACT")

# --- SETUP ---
w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)
player_address = account.address

print(f"🕵️  Acting as Player: {player_address}")

# ABI for 'transfer'
ERC20_ABI = [
    {
        "constant": False,
        "inputs": [{"name": "_to", "type": "address"}, {"name": "_value", "type": "uint256"}],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    }
]

contract = w3.eth.contract(address=FXRP_CONTRACT, abi=ERC20_ABI)

def step_1_send_money():
    print(f"\n1️⃣  Sending {ITEM_COST} FXRP to Treasury...")
    
    # 1. Build Transaction
    amount_wei = w3.to_wei(ITEM_COST, 'ether')
    nonce = w3.eth.get_transaction_count(player_address)
    
    tx = contract.functions.transfer(
        Web3.to_checksum_address(TREASURY_ADDRESS),
        amount_wei
    ).build_transaction({
        'chainId': 114, # Coston2
        'gas': 200000,
        'gasPrice': w3.eth.gas_price,
        'nonce': nonce,
    })
    
    # 2. Sign & Send
    signed_tx = w3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)
    
    print(f"⏳ Transaction sent! Hash: {w3.to_hex(tx_hash)}")
    print("   Waiting for confirmation...")
    
    # 3. Wait for Receipt
    receipt = w3.eth.wait_for_transaction_receipt(tx_hash)
    
    if receipt.status == 1:
        print("✅ Payment Confirmed on Blockchain!")
        return w3.to_hex(tx_hash)
    else:
        raise Exception("❌ Transaction Failed!")

def step_2_call_api(tx_hash):
    print(f"\n2️⃣  Calling Backend API to Claim Item...")
    
    # 1. Create Signature (Auth)
    # This message MUST match what your backend expects. 
    # For now, we assume a simple test message or whatever build_action_message produces.
    # If your backend checks specific message formats, update this string!
    msg_text = "test_message" 
    message_hash = encode_defunct(text=msg_text)
    signature = account.sign_message(message_hash).signature.hex()
    
    # 2. Build Payload
    payload = {
        "proof": {
            "address": player_address,
            "message": msg_text,
            "signature": signature
        },
        "tileId": 5,        # Trying to buy Tile 5 (Reading Railroad, etc.)
        "txHash": tx_hash   # <--- THE PROOF OF PAYMENT
    }
    
    # 3. Send Request
    try:
        response = requests.post(f"{API_URL}/buy", json=payload)
        print(f"📬 Response [{response.status_code}]:")
        print(json.dumps(response.json(), indent=2))
        
        if response.status_code == 200:
            print("\n🎉 SUCCESS! You bought the item with real fake-money.")
        else:
            print("\n❌ FAIL. Backend rejected it.")
            
    except Exception as e:
        print(f"❌ API Error: {e}")

if __name__ == "__main__":
    try:
        # Execute Flow
        real_tx_hash = step_1_send_money()
        step_2_call_api(real_tx_hash)
    except Exception as e:
        print(f"\n💥 CRITICAL ERROR: {e}")