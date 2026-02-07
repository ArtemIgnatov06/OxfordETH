import os
import json
from web3 import Web3
from dotenv import load_dotenv

load_dotenv()

class FxrpChain:
    def __init__(self):
        # 1. Connect to Coston2
        rpc_url = os.getenv("FLARE_RPC_URL", "https://coston2-api.flare.network/ext/C/rpc")
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        
        # 2. Load the Contract Address
        self.contract_address = os.getenv("FXRP_CONTRACT")
        if not self.contract_address:
            raise ValueError("❌ Missing FXRP_CONTRACT in .env")

        # 3. LINKING STEP: Load the ABI from your JSON file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Pointing to ../abis/GameFXRP.json
        json_path = os.path.join(base_dir, "..", "abis", "GameFXRP.json")
        
        try:
            with open(json_path, "r") as f:
                artifact = json.load(f)
                self.abi = artifact["abi"]
        except FileNotFoundError:
            # Fallback to the minimal ABI if file is missing
            print("⚠️ GameFXRP.json not found, using minimal ABI")
            self.abi = [...] # (Keep your old hardcoded ABI here as backup)

        # 4. Initialize Contract
        self.contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(self.contract_address),
            abi=self.abi
        )

    def get_balance(self, address: str) -> float:
        """Reads on-chain balance"""
        if not self.w3.is_connected(): 
            return 0.0
        try:
            raw = self.contract.functions.balanceOf(Web3.to_checksum_address(address)).call()
            return float(self.w3.from_wei(raw, 'ether'))
        except Exception as e:
            print(f"Error reading balance: {e}")
            return 0.0

# Create a single instance to be used by other files
fxrp_client = FxrpChain()