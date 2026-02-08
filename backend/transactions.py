# backend/transactions.py
from dataclasses import dataclass
from typing import Dict, Optional, Literal
import os

from web3 import Web3
from web3._utils.events import get_event_data
from hexbytes import HexBytes

# IMPORTANT: correct import for your repo structure
from chain.chain_fxrp import fxrp_client

SettlementKind = Literal["buy", "trade"]


@dataclass
class PendingSettlement:
    kind: SettlementKind
    from_addr: str
    to_addr: str
    amount_raw: int
    tile_id: int
    offer_id: Optional[str] = None

    def to_front(self) -> Dict:
        return {
            "kind": self.kind,
            "from": self.from_addr,
            "to": self.to_addr,
            "amountRaw": int(self.amount_raw),
            "tileId": int(self.tile_id),
            "offerId": self.offer_id,
        }


class TxVerifier:
    """All on-chain FXRP settlement verification."""

    def verify_fxrp_transfer(
        self,
        *,
        tx_hash: str,
        expected_from: str,
        expected_to: str,
        expected_amount_raw: int,
    ) -> None:
        w3 = fxrp_client.w3
        receipt = w3.eth.get_transaction_receipt(tx_hash)

        if receipt is None:
            raise ValueError("tx not found / not mined")
        if receipt.get("status") != 1:
            raise ValueError("tx failed")

        min_conf = int(os.getenv("MIN_CONFIRMATIONS", "1"))
        conf = w3.eth.block_number - receipt["blockNumber"] + 1
        if conf < min_conf:
            raise ValueError(f"not enough confirmations ({conf}/{min_conf})")

        contract = fxrp_client.contract
        fxrp_addr = Web3.to_checksum_address(contract.address)

        transfer_topic = Web3.keccak(text="Transfer(address,address,uint256)")
        event_abi = contract.events.Transfer._get_event_abi()

        ef = Web3.to_checksum_address(expected_from)
        et = Web3.to_checksum_address(expected_to)
        ev_amt = int(expected_amount_raw)

        for log in receipt.get("logs", []):
            if Web3.to_checksum_address(log["address"]) != fxrp_addr:
                continue

            topics = log.get("topics", [])
            if not topics or HexBytes(topics[0]) != HexBytes(transfer_topic):
                continue

            decoded = get_event_data(w3.codec, event_abi, log)
            args = decoded["args"]

            if (
                Web3.to_checksum_address(args["from"]) == ef
                and Web3.to_checksum_address(args["to"]) == et
                and int(args["value"]) == ev_amt
            ):
                return

        raise ValueError("no matching FXRP Transfer found in tx")
