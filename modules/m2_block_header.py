"""Block header parsing and Proof of Work verification module."""

from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from api.blockchain_client import (
    get_block_header_hex,
    get_blockstream_block,
    get_latest_block_hash,
)


def _target_from_bits(bits: int) -> int:
    """Decode Bitcoin's compact target representation."""
    exponent = bits >> 24
    mantissa = bits & 0xFFFFFF
    if exponent <= 3:
        return mantissa >> (8 * (3 - exponent))
    return mantissa << (8 * (exponent - 3))


def _leading_zero_bits(hex_hash: str) -> int:
    """Count leading zero bits in a 256-bit hash."""
    value = int(hex_hash, 16)
    return 256 if value == 0 else 256 - value.bit_length()


def _double_sha256_block_hash(header: bytes) -> str:
    """Return Bitcoin's displayed block hash for an 80-byte header."""
    digest = hashlib.sha256(hashlib.sha256(header).digest()).digest()
    return digest[::-1].hex()


def _parse_header(header_hex: str) -> dict:
    """Parse the six fields of a Bitcoin block header."""
    header = bytes.fromhex(header_hex)
    if len(header) != 80:
        raise ValueError(f"Expected an 80-byte header, got {len(header)} bytes.")

    version_bytes = header[0:4]
    prev_hash_bytes = header[4:36]
    merkle_root_bytes = header[36:68]
    timestamp_bytes = header[68:72]
    bits_bytes = header[72:76]
    nonce_bytes = header[76:80]

    bits = int.from_bytes(bits_bytes, byteorder="little")
    computed_hash = _double_sha256_block_hash(header)
    target = _target_from_bits(bits)

    return {
        "header_bytes": header,
        "computed_hash": computed_hash,
        "target": target,
        "fields": [
            {
                "Field": "Version",
                "Bytes": "0-3",
                "Raw little-endian hex": version_bytes.hex(),
                "Decoded value": int.from_bytes(version_bytes, "little"),
            },
            {
                "Field": "Previous block hash",
                "Bytes": "4-35",
                "Raw little-endian hex": prev_hash_bytes.hex(),
                "Decoded value": prev_hash_bytes[::-1].hex(),
            },
            {
                "Field": "Merkle root",
                "Bytes": "36-67",
                "Raw little-endian hex": merkle_root_bytes.hex(),
                "Decoded value": merkle_root_bytes[::-1].hex(),
            },
            {
                "Field": "Timestamp",
                "Bytes": "68-71",
                "Raw little-endian hex": timestamp_bytes.hex(),
                "Decoded value": int.from_bytes(timestamp_bytes, "little"),
            },
            {
                "Field": "Bits",
                "Bytes": "72-75",
                "Raw little-endian hex": bits_bytes.hex(),
                "Decoded value": bits,
            },
            {
                "Field": "Nonce",
                "Bytes": "76-79",
                "Raw little-endian hex": nonce_bytes.hex(),
                "Decoded value": int.from_bytes(nonce_bytes, "little"),
            },
        ],
    }


@st.cache_data(ttl=60)
def _load_block_header(block_hash: str) -> tuple[dict, str]:
    return get_blockstream_block(block_hash), get_block_header_hex(block_hash)


def render() -> None:
    """Render the M2 panel."""
    st.header("M2 - Block Header Analyzer")

    try:
        latest_hash = get_latest_block_hash()
    except Exception as exc:
        st.error(f"Error fetching latest block hash: {exc}")
        return

    use_latest = st.toggle("Analyze latest block", value=True, key="m2_use_latest")
    block_hash = latest_hash
    if not use_latest:
        block_hash = st.text_input(
            "Block hash",
            placeholder="Enter a Bitcoin block hash",
            key="m2_hash",
        ).strip()

    if st.button("Refresh block header", key="m2_refresh"):
        _load_block_header.clear()

    if not block_hash:
        st.info("Enter a block hash or enable latest block analysis.")
        return

    try:
        block, header_hex = _load_block_header(block_hash)
        parsed = _parse_header(header_hex)
    except Exception as exc:
        st.error(f"Error analyzing block header: {exc}")
        return

    computed_hash = parsed["computed_hash"]
    target = parsed["target"]
    target_hex = f"{target:064x}"
    pow_is_valid = int(computed_hash, 16) < target

    metric_cols = st.columns(4)
    metric_cols[0].metric("Height", f"{block['height']:,}")
    metric_cols[1].metric("Header size", f"{len(parsed['header_bytes'])} bytes")
    metric_cols[2].metric("Leading zero bits", _leading_zero_bits(computed_hash))
    metric_cols[3].metric("Proof of Work", "Valid" if pow_is_valid else "Invalid")

    st.subheader("80-Byte Header Structure")
    timestamp = pd.to_datetime(parsed["fields"][3]["Decoded value"], unit="s")
    field_rows = parsed["fields"].copy()
    field_rows[3] = field_rows[3].copy()
    field_rows[3]["Decoded value"] = f"{field_rows[3]['Decoded value']} ({timestamp})"
    st.dataframe(pd.DataFrame(field_rows).astype(str), width="stretch", hide_index=True)

    st.subheader("Local Hash Verification")
    st.caption(
        "The block hash below is computed locally with hashlib as "
        "SHA256(SHA256(header)). The digest is reversed for Bitcoin's display order."
    )
    st.code(
        f"raw header = {header_hex}\n"
        f"computed hash = {computed_hash}\n"
        f"API block hash = {block['id']}\n"
        f"target        = {target_hex}\n"
        f"hash < target = {pow_is_valid}",
        language="text",
    )

    if computed_hash == block["id"] and pow_is_valid:
        st.success("The locally computed hash matches the API hash and is below target.")
    elif computed_hash != block["id"]:
        st.error("The locally computed hash does not match the API block hash.")
    else:
        st.error("The hash matches the API block hash, but it is not below target.")

    st.subheader("Byte Order Notes")
    st.markdown(
        """
        - Integer fields are decoded from little-endian bytes.
        - Previous block hash and Merkle root are stored internally in little-endian byte order.
        - The displayed block hash reverses the raw SHA-256 digest bytes.
        """
    )
