# auth_sig.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

from web3 import Web3
from eth_account.messages import encode_defunct
from eth_account import Account


@dataclass
class SigProof:
    address: str
    message: str
    signature: str


def build_action_message(*, game_id: str, chain_id: int, player_index: int, action: str, params: str, nonce: int) -> str:
    return (
        "OxfordETH FlarePoly Action\n"
        f"Game: {game_id}\n"
        f"ChainId: {chain_id}\n"
        f"PlayerIndex: {player_index}\n"
        f"Action: {action}\n"
        f"Params: {params}\n"
        f"Nonce: {nonce}\n"
        "Sign this to prove wallet ownership for this action."
    )


def verify_proof(proof: SigProof) -> bool:
    msg = encode_defunct(text=proof.message)
    recovered = Account.recover_message(msg, signature=proof.signature)
    return Web3.to_checksum_address(recovered) == Web3.to_checksum_address(proof.address)
