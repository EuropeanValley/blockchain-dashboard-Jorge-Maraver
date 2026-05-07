"""Merkle proof verification dashboard module."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from api.blockchain_client import (
    get_block_txids,
    get_blockstream_block,
    get_latest_block_hash,
    get_tx_merkle_proof,
)


def _hash_pair(left_txid: str, right_txid: str) -> str:
    """Hash two transaction ids as Bitcoin Merkle tree nodes."""
    left = bytes.fromhex(left_txid)[::-1]
    right = bytes.fromhex(right_txid)[::-1]
    digest = hashlib.sha256(hashlib.sha256(left + right).digest()).digest()
    return digest[::-1].hex()


def _verify_merkle_path(txid: str, proof: dict) -> tuple[str, list[dict]]:
    """Rebuild the Merkle root from a transaction id and its proof."""
    current_hash = txid
    position = int(proof["pos"])
    steps = []

    for level, sibling_hash in enumerate(proof["merkle"], start=1):
        if position % 2 == 0:
            left_hash = current_hash
            right_hash = sibling_hash
            side = "right sibling"
        else:
            left_hash = sibling_hash
            right_hash = current_hash
            side = "left sibling"

        parent_hash = _hash_pair(left_hash, right_hash)
        steps.append(
            {
                "Level": level,
                "Position": position,
                "Sibling side": side,
                "Left hash": left_hash,
                "Right hash": right_hash,
                "Parent hash": parent_hash,
            }
        )
        current_hash = parent_hash
        position //= 2

    return current_hash, steps


@st.cache_data(ttl=60)
def _load_latest_merkle_data() -> tuple[dict, list[str]]:
    block_hash = get_latest_block_hash()
    block = get_blockstream_block(block_hash)
    return block, get_block_txids(block_hash)


@st.cache_data(ttl=300)
def _load_merkle_proof(txid: str) -> dict:
    return get_tx_merkle_proof(txid)


def render() -> None:
    """Render the M5 panel."""
    st.header("M5 - Merkle Proof Verifier")

    try:
        latest_block, txids = _load_latest_merkle_data()
    except Exception as exc:
        st.error(f"Error loading latest block transactions: {exc}")
        return

    if not txids:
        st.warning("The latest block did not return transaction ids.")
        return

    col_settings, col_info = st.columns([1, 2])
    with col_settings:
        tx_index = st.number_input(
            "Transaction index",
            min_value=0,
            max_value=len(txids) - 1,
            value=min(1, len(txids) - 1),
            step=1,
            key="m5_tx_index",
        )
        if st.button("Refresh Merkle data", key="m5_refresh"):
            _load_latest_merkle_data.clear()
            _load_merkle_proof.clear()
    with col_info:
        st.caption(
            "This module verifies that a selected transaction belongs to the latest "
            "Bitcoin block by rebuilding the Merkle root step by step."
        )

    selected_txid = txids[int(tx_index)]

    try:
        proof = _load_merkle_proof(selected_txid)
        computed_root, steps = _verify_merkle_path(selected_txid, proof)
    except Exception as exc:
        st.error(f"Error verifying Merkle proof: {exc}")
        return

    api_root = latest_block["merkle_root"]
    proof_is_valid = computed_root == api_root

    metric_cols = st.columns(5)
    metric_cols[0].metric("Block height", f"{latest_block['height']:,}")
    metric_cols[1].metric("Transactions", f"{len(txids):,}")
    metric_cols[2].metric("TX position", proof["pos"])
    metric_cols[3].metric("Proof depth", len(proof["merkle"]))
    metric_cols[4].metric("Proof", "Valid" if proof_is_valid else "Invalid")

    st.subheader("Selected Transaction")
    st.code(
        f"block hash  = {latest_block['id']}\n"
        f"txid        = {selected_txid}\n"
        f"merkle root = {api_root}",
        language="text",
    )

    st.subheader("Step-by-Step Merkle Path")
    st.caption(
        "At each level, the transaction hash is paired with its sibling, both hashes "
        "are converted to internal byte order, and Bitcoin double-SHA256 is applied."
    )
    st.dataframe(pd.DataFrame(steps), width="stretch", hide_index=True)

    st.subheader("Verification Result")
    st.code(
        f"computed root = {computed_root}\n"
        f"API root      = {api_root}\n"
        f"match         = {proof_is_valid}",
        language="text",
    )

    if proof_is_valid:
        st.success("The computed Merkle root matches the block header Merkle root.")
    else:
        st.error("The computed Merkle root does not match the block header Merkle root.")
