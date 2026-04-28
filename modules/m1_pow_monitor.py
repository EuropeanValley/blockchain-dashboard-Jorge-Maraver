"""Proof of Work monitoring dashboard module."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import get_recent_blocks

try:
    from streamlit_autorefresh import st_autorefresh
except ImportError:  # pragma: no cover - shown in the UI when dependency is missing.
    st_autorefresh = None


def _target_from_bits(bits: int) -> int:
    """Decode Bitcoin's compact target representation."""
    exponent = bits >> 24
    mantissa = bits & 0xFFFFFF
    if exponent <= 3:
        return mantissa >> (8 * (3 - exponent))
    return mantissa << (8 * (exponent - 3))


def _leading_zero_bits(hex_hash: str) -> int:
    """Count leading zero bits in a 256-bit block hash."""
    value = int(hex_hash, 16)
    return 256 if value == 0 else 256 - value.bit_length()


def _format_hashrate(hashrate: float) -> str:
    """Format hashes per second using mining-friendly units."""
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s"]
    value = hashrate
    for unit in units:
        if value < 1000 or unit == units[-1]:
            return f"{value:,.2f} {unit}"
        value /= 1000
    return f"{value:,.2f} ZH/s"


@st.cache_data(ttl=60)
def _load_recent_blocks(n_blocks: int) -> list[dict]:
    return get_recent_blocks(n_blocks)


def render() -> None:
    """Render the M1 panel."""
    st.header("M1 - Proof of Work Monitor")

    col_settings, col_status = st.columns([1, 2])
    with col_settings:
        n_blocks = st.slider(
            "Recent blocks",
            min_value=20,
            max_value=100,
            value=40,
            step=10,
            key="m1_recent_blocks",
        )
    with col_status:
        auto_refresh = st.toggle("Auto refresh every 60 seconds", value=True)
        if auto_refresh and st_autorefresh is not None:
            st_autorefresh(interval=60_000, key="m1_autorefresh")
        elif auto_refresh:
            st.warning("Install streamlit-autorefresh to enable automatic updates.")

    if st.button("Refresh now", key="m1_refresh"):
        _load_recent_blocks.clear()

    try:
        blocks = _load_recent_blocks(n_blocks)
    except Exception as exc:
        st.error(f"Error fetching Bitcoin blocks: {exc}")
        return

    if len(blocks) < 2:
        st.warning("Not enough block data was returned by the API.")
        return

    latest = blocks[0]
    target = _target_from_bits(int(latest["bits"]))
    target_hex = f"{target:064x}"
    leading_zero_bits = _leading_zero_bits(latest["id"])
    leading_zero_hex = len(latest["id"]) - len(latest["id"].lstrip("0"))

    ordered_blocks = sorted(blocks, key=lambda block: block["height"])
    rows = []
    for previous, current in zip(ordered_blocks, ordered_blocks[1:]):
        seconds = current["timestamp"] - previous["timestamp"]
        if seconds > 0:
            rows.append(
                {
                    "Height": current["height"],
                    "Timestamp": pd.to_datetime(current["timestamp"], unit="s"),
                    "Block time (seconds)": seconds,
                    "Block time (minutes)": seconds / 60,
                }
            )

    df = pd.DataFrame(rows)
    average_seconds = df["Block time (seconds)"].mean()
    hashrate_from_window = latest["difficulty"] * 2**32 / average_seconds
    hashrate_target_interval = latest["difficulty"] * 2**32 / 600

    metric_cols = st.columns(5)
    metric_cols[0].metric("Latest height", f"{latest['height']:,}")
    metric_cols[1].metric("Difficulty", f"{latest['difficulty']:,.0f}")
    metric_cols[2].metric("Nonce", f"{latest['nonce']:,}")
    metric_cols[3].metric("Transactions", f"{latest['tx_count']:,}")
    metric_cols[4].metric("Bits", latest["bits"])

    st.subheader("Target Threshold")
    st.caption(
        "The block hash must be numerically below the target decoded from bits. "
        "More leading zero bits mean a smaller valid hash region in the 256-bit space."
    )
    st.code(
        f"hash   = {latest['id']}\n"
        f"target = {target_hex}\n"
        f"hash < target: {int(latest['id'], 16) < target}",
        language="text",
    )
    target_cols = st.columns(3)
    target_cols[0].metric("Leading zero hex digits", leading_zero_hex)
    target_cols[1].metric("Leading zero bits", leading_zero_bits)
    target_cols[2].metric("Target zero-bit prefix", 256 - target.bit_length())

    st.subheader("Inter-Block Time Distribution")
    st.caption(
        "Bitcoin mining is modeled as a Poisson process, so block arrival times "
        "are expected to follow an exponential distribution around a 600 second target."
    )
    fig = px.histogram(
        df,
        x="Block time (seconds)",
        nbins=20,
        title=f"Time Between Last {len(blocks)} Blocks",
        labels={"Block time (seconds)": "Seconds between blocks"},
    )
    fig.add_vline(
        x=600,
        line_dash="dash",
        line_color="red",
        annotation_text="10 min target",
    )
    fig.update_layout(yaxis_title="Number of blocks")
    st.plotly_chart(fig, width="stretch")

    st.subheader("Estimated Network Hash Rate")
    hash_cols = st.columns(3)
    hash_cols[0].metric("Average block time", f"{average_seconds:,.1f} s")
    hash_cols[1].metric("Window estimate", _format_hashrate(hashrate_from_window))
    hash_cols[2].metric("600s baseline", _format_hashrate(hashrate_target_interval))

    st.dataframe(
        df.sort_values("Height", ascending=False),
        width="stretch",
        hide_index=True,
    )
