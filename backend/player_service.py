# 1. Import Security
from backend.auth_sig import verify_proof, SigProof, build_action_message

# 2. Import Blockchain Connection
from backend.chain.chain_fxrp import fxrp_client

class PlayerService:
    
    def buy_item(self, proof: SigProof, game_id: str, item_name: str, cost: float):
        """
        Links everything together:
        1. Verifies Signature (auth_sig)
        2. Checks Balance (chain_fxrp)
        3. Grants Item (Game Logic)
        """
        
        # --- LINK 1: SECURITY CHECK ---
        # Verify the user actually signed this request
        if not verify_proof(proof):
            raise PermissionError("❌ Invalid Signature: You are not the owner of this wallet.")

        # --- LINK 2: BLOCKCHAIN CHECK ---
        # Check if they have enough FXRP on Coston2
        balance = fxrp_client.get_balance(proof.address)
        print(f"🔍 Wallet {proof.address} Balance: {balance} FXRP")

        if balance < cost:
            raise ValueError(f"❌ Insufficient Funds: You need {cost} FXRP but have {balance}.")

        # --- LINK 3: GAME LOGIC ---
        # If we get here, they are verified and rich enough.
        # TODO: Add your code here to update the database/game state
        print(f"✅ SUCCESS: {proof.address} bought {item_name}!")
        
        return {
            "status": "success",
            "item": item_name,
            "remaining_balance": balance  # Note: Real balance updates require a transaction
        }