# chain_fxrp.py
from __future__ import annotations
import os
from dataclasses import dataclass
from typing import Optional, Tuple

from web3 import Web3

# Minimal ERC-20 ABI: balanceOf, decimals, Transfer event
ERC20_ABI = [
    {"name": "balanceOf", "type": "function", "stateMutability": "view",
     "inputs": [{"name": "owner", "type": "address"}],
     "outputs": [{"name": "", "type": "uint256"}]},
    {"name": "decimals", "type": "function", "stateMutability": "view",
     "inputs": [], "outputs": [{"name": "", "type": "uint8"}]},
    {"anonymous": False, "type": "event", "name": "Transfer",
     "inputs": [
         {"indexed": True, "name": "from", "type": "address"},
         {"indexed": True, "name": "to", "type": "address"},
         {"indexed": False, "name": "value", "type": "uint256"},
     ]},
]


def make_w3() -> Web3:
    rpc = os.getenv("FLARE_RPC_URL", "").strip()
    if not rpc:
        raise RuntimeError("Set FLARE_RPC_URL (e.g. Coston2 RPC)")
    w3 = Web3(Web3.HTTPProvider(rpc))
    if not w3.is_connected():
        raise RuntimeError("Cannot connect to FLARE_RPC_URL")
    return w3


@dataclass
class FxrpChain:
    w3: Web3
    fxrp_address: str

    @classmethod
    def from_env(cls) -> "FxrpChain":
        w3 = make_w3()
        fxrp = os.getenv("FXRP_CONTRACT", "").strip()
        if not fxrp:
            raise RuntimeError("Set FXRP_CONTRACT to your deployed ERC-20 address")
        return cls(w3=w3, fxrp_address=Web3.to_checksum_address(fxrp))

    def contract(self):
        return self.w3.eth.contract(address=self.fxrp_address, abi=ERC20_ABI)

    def decimals(self) -> int:
        return int(self.contract().functions.decimals().call())

    def balance_of(self, address: str) -> int:
        return int(self.contract().functions.balanceOf(Web3.to_checksum_address(address)).call())

    def balance_of_float(self, address: str) -> float:
        d = self.decimals()
        return self.balance_of(address) / (10 ** d)

    def verify_erc20_transfer(
        self,
        *,
        tx_hash: str,
        expected_from: str,
        expected_to: str,
        expected_amount_raw: int,
        min_confirmations: int = 1,
    ) -> Tuple[bool, str]:
        """
        Verifies that tx_hash includes a Transfer(from,to,value) on FXRP contract.
        """
        try:
            receipt = self.w3.eth.get_transaction_receipt(tx_hash)
        except Exception:
            return False, "tx not found / not mined"

        if receipt is None or receipt.get("status") != 1:
            return False, "tx failed"

        # confirmations
        latest = self.w3.eth.block_number
        conf = latest - receipt["blockNumber"] + 1
        if conf < min_confirmations:
            return False, f"not enough confirmations ({conf}/{min_confirmations})"

        c = self.contract()
        logs = c.events.Transfer().process_receipt(receipt)

        ef = Web3.to_checksum_address(expected_from)
        et = Web3.to_checksum_address(expected_to)

        for ev in logs:
            args = ev["args"]
            if (
                Web3.to_checksum_address(args["from"]) == ef
                and Web3.to_checksum_address(args["to"]) == et
                and int(args["value"]) == int(expected_amount_raw)
            ):
                return True, "ok"

        return False, "no matching FXRP Transfer found in tx"


# --- Optional FTSO pricing (fallback-safe) ---

class PriceOracle:
    """
    Optional: if env is set, use FTSO-based price. Otherwise fallback.
    You can plug real FTSO read here when you have the exact contract/ABI.
    """
    def __init__(self):
        self.enabled = False
        # Example: you can later load ABI+address similarly to FxrpChain.
        # For now we keep a safe fallback for the hackathon.

    def fxrp_usd(self) -> Optional[float]:
        """
        Return FXRP price in USD if configured, else None.
        """
        return None
