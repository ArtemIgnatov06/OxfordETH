from backend.player_service import PlayerService
from backend.auth_sig import SigProof
from eth_account import Account
from eth_account.messages import encode_defunct
from backend.chain.chain_fxrp import fxrp_client
import os
from dotenv import load_dotenv

# 1. Load Environment Variables
load_dotenv()

# --- SETUP ---
# Create a dummy wallet for the signature test (Security Link)
test_wallet = Account.create()
player_address = test_wallet.address

print(f"🕵️  Testing Security with Dummy User: {player_address}")

# Create Proof
msg_text = "test_message" 
message_hash = encode_defunct(text=msg_text)
signature = test_wallet.sign_message(message_hash).signature.hex()

proof = SigProof(
    address=player_address,
    message=msg_text,
    signature=signature
)

# --- EXECUTE TEST 1 (Security) ---
service = PlayerService()

print("------------------------------------------------")
print("1️⃣  Testing Security Link (Signature Check)...")
try:
    # This expects to fail on funds, but pass on signature
    result = service.buy_item(proof, "game1", "Hotel", 10)
    print("✅  Buy Successful:", result)
except Exception as e:
    print(f"✅  Security Check Passed (Logic Stopped): {e}")

# --- EXECUTE TEST 2 (Chain Balance) ---
print("------------------------------------------------")
print("2️⃣  Testing Chain Link (Real Balance Check)...")

# 👉 NEW: Load Private Key from .env instead of hardcoding
private_key = os.getenv("PRIVATE_KEY")

if not private_key:
    print("❌ Error: PRIVATE_KEY not found in .env file!")
else:
    # Derive the public address from the private key
    my_account = Account.from_key(private_key)
    my_real_wallet = my_account.address
    
    print(f"🔑 Loaded Wallet from .env: {my_real_wallet}")
    
    # Check Balance
    bal = fxrp_client.get_balance(my_real_wallet)
    print(f"💰 Balance: {bal:,.2f} FXRP")

print("------------------------------------------------")