# In state.py imports:
from chain.chain_fxrp import fxrp_client

# Inside your Game class -> buy method:
def buy(self, proof: SigProof, tile_id: int, tx_hash: str = None):
    # 1. Calculate Cost (Your existing logic)
    cost = self.get_tile_cost(tile_id) 

    # 2. VERIFY PAYMENT (The new part)
    if cost > 0:
        if not tx_hash:
            raise ValueError("❌ Payment required: Missing txHash")
        
        print(f"🕵️ Verifying payment of {cost} FXRP in tx {tx_hash}...")
        
        valid = fxrp_client.verify_payment(
            tx_hash=tx_hash,
            expected_payer=proof.address,
            expected_amount=cost
        )
        
        if not valid:
            raise ValueError("❌ Payment verification failed. Check transaction.")

    # 3. If we get here, payment is real. Proceed with ownership logic.
    self.assign_tile_to_player(tile_id, proof.address)
    print("✅ Property purchased!")