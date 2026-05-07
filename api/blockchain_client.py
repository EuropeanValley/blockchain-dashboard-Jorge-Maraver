"""
Blockchain API client.

Provides helper functions to fetch blockchain data from public APIs.
"""

import requests

BASE_URL = "https://blockchain.info"
BLOCKSTREAM_BASE_URL = "https://blockstream.info/api"


def get_latest_block() -> dict:
    """Return the latest block summary."""
    response = requests.get(f"{BASE_URL}/latestblock", timeout=10)
    response.raise_for_status()
    return response.json()


def get_block(block_hash: str) -> dict:
    """Return full details for a block identified by *block_hash*."""
    response = requests.get(
        f"{BASE_URL}/rawblock/{block_hash}", timeout=10
    )
    response.raise_for_status()
    return response.json()


def get_current_difficulty() -> float:
    """Return the current Bitcoin mining difficulty."""
    response = requests.get(f"{BASE_URL}/q/getdifficulty", timeout=10)
    response.raise_for_status()
    return float(response.text)


def get_recent_blocks(n_blocks: int = 30) -> list[dict]:
    """Return recent Bitcoin blocks from newest to oldest."""
    response = requests.get(f"{BLOCKSTREAM_BASE_URL}/blocks/tip/height", timeout=10)
    response.raise_for_status()
    next_height = int(response.text)

    blocks: list[dict] = []
    while len(blocks) < n_blocks and next_height > 0:
        response = requests.get(
            f"{BLOCKSTREAM_BASE_URL}/blocks/{next_height}", timeout=10
        )
        response.raise_for_status()
        page = response.json()
        if not page:
            break
        blocks.extend(page)
        next_height = min(block["height"] for block in page) - 1

    return blocks[:n_blocks]


def get_latest_block_hash() -> str:
    """Return the current Bitcoin tip hash."""
    response = requests.get(f"{BLOCKSTREAM_BASE_URL}/blocks/tip/hash", timeout=10)
    response.raise_for_status()
    return response.text.strip()


def get_latest_block_height() -> int:
    """Return the current Bitcoin tip height."""
    response = requests.get(f"{BLOCKSTREAM_BASE_URL}/blocks/tip/height", timeout=10)
    response.raise_for_status()
    return int(response.text)


def get_block_hash_by_height(height: int) -> str:
    """Return the block hash at a given height."""
    response = requests.get(f"{BLOCKSTREAM_BASE_URL}/block-height/{height}", timeout=10)
    response.raise_for_status()
    return response.text.strip()


def get_blockstream_block(block_hash: str) -> dict:
    """Return Blockstream metadata for a block identified by *block_hash*."""
    response = requests.get(f"{BLOCKSTREAM_BASE_URL}/block/{block_hash}", timeout=10)
    response.raise_for_status()
    return response.json()


def get_blockstream_block_by_height(height: int) -> dict:
    """Return Blockstream metadata for a block identified by height."""
    return get_blockstream_block(get_block_hash_by_height(height))


def get_block_header_hex(block_hash: str) -> str:
    """Return the raw 80-byte block header as a hexadecimal string."""
    response = requests.get(
        f"{BLOCKSTREAM_BASE_URL}/block/{block_hash}/header", timeout=10
    )
    response.raise_for_status()
    return response.text.strip()


def get_block_txids(block_hash: str) -> list[str]:
    """Return all transaction ids in a block."""
    response = requests.get(f"{BLOCKSTREAM_BASE_URL}/block/{block_hash}/txids", timeout=10)
    response.raise_for_status()
    return response.json()


def get_tx_merkle_proof(txid: str) -> dict:
    """Return the Merkle proof for a transaction id."""
    response = requests.get(
        f"{BLOCKSTREAM_BASE_URL}/tx/{txid}/merkle-proof", timeout=10
    )
    response.raise_for_status()
    return response.json()


def get_difficulty_history(n_points: int = 100) -> list[dict]:
    """Return the last *n_points* difficulty values as a list of dicts."""
    response = requests.get(
        f"{BASE_URL}/charts/difficulty",
        params={"timespan": "1year", "format": "json", "sampled": "true"},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()
    return data.get("values", [])[-n_points:]


if __name__ == "__main__":
    block = get_block(get_latest_block()["hash"])
    difficulty = get_current_difficulty()
    # Observation: the block hash starts with leading zero hex digits, evidence of Proof of Work.
    # Observation: the bits field compactly encodes the target threshold used to validate the hash.
    print(f"Block height: {block['height']}")
    print(f"Hash: {block['hash']}")
    print(f"Difficulty: {difficulty} | Bits: {block['bits']}")
    print(f"Nonce: {block['nonce']}")
    print(f"Transactions: {block['n_tx']}")
