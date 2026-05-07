"""Bitcoin security score and 51% attack cost estimator."""

from __future__ import annotations

import math

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import get_recent_blocks


@st.cache_data(ttl=300)
def _load_recent_blocks(n_blocks: int) -> list[dict]:
    return get_recent_blocks(n_blocks)


def _format_hashrate(hashrate: float) -> str:
    units = ["H/s", "KH/s", "MH/s", "GH/s", "TH/s", "PH/s", "EH/s", "ZH/s"]
    value = hashrate
    for unit in units:
        if value < 1000 or unit == units[-1]:
            return f"{value:,.2f} {unit}"
        value /= 1000
    return f"{value:,.2f} ZH/s"


def _estimate_hashrate(blocks: list[dict]) -> tuple[float, float]:
    ordered_blocks = sorted(blocks, key=lambda block: block["height"])
    intervals = [
        current["timestamp"] - previous["timestamp"]
        for previous, current in zip(ordered_blocks, ordered_blocks[1:])
        if current["timestamp"] > previous["timestamp"]
    ]
    average_seconds = sum(intervals) / len(intervals)
    latest_difficulty = blocks[0]["difficulty"]
    return latest_difficulty * 2**32 / average_seconds, average_seconds


def _hourly_energy_cost(hashrate_hs: float, efficiency_j_per_th: float, usd_per_kwh: float) -> float:
    th_per_second = hashrate_hs / 1e12
    watts = th_per_second * efficiency_j_per_th
    return (watts / 1000) * usd_per_kwh


def _catch_up_probability(confirmations: int, attacker_share: float) -> float:
    """Approximate double-spend catch-up probability from Nakamoto section 11."""
    if attacker_share <= 0:
        return 0.0
    if attacker_share >= 0.5:
        return 1.0
    honest_share = 1 - attacker_share
    return (attacker_share / honest_share) ** confirmations


def render() -> None:
    """Render the M6 panel."""
    st.header("M6 - Security Score")

    settings_col, explanation_col = st.columns([1, 2])
    with settings_col:
        n_blocks = st.slider(
            "Hash rate window blocks",
            min_value=40,
            max_value=160,
            value=80,
            step=20,
            key="m6_n_blocks",
        )
        electricity_price = st.number_input(
            "Electricity price (USD/kWh)",
            min_value=0.01,
            max_value=1.00,
            value=0.07,
            step=0.01,
            key="m6_electricity",
        )
        efficiency = st.number_input(
            "ASIC efficiency (J/TH)",
            min_value=5.0,
            max_value=100.0,
            value=20.0,
            step=1.0,
            key="m6_efficiency",
        )
        hardware_usd_per_th = st.number_input(
            "Hardware cost (USD/TH)",
            min_value=1.0,
            max_value=100.0,
            value=15.0,
            step=1.0,
            key="m6_hardware_cost",
        )
        attacker_share = st.slider(
            "Attacker hash share for confirmation risk",
            min_value=0.05,
            max_value=0.49,
            value=0.30,
            step=0.01,
            key="m6_attacker_share",
        )
        if st.button("Refresh security data", key="m6_refresh"):
            _load_recent_blocks.clear()

    with explanation_col:
        st.caption(
            "This module estimates the scale of a 51% attack from live network hash "
            "rate and user-adjustable ASIC assumptions. It also visualizes the "
            "confirmation-depth risk model from Nakamoto's double-spend analysis."
        )

    try:
        blocks = _load_recent_blocks(n_blocks)
        network_hashrate, average_seconds = _estimate_hashrate(blocks)
    except Exception as exc:
        st.error(f"Error loading security data: {exc}")
        return

    attack_hashrate = network_hashrate * 1.01
    hourly_cost = _hourly_energy_cost(attack_hashrate, efficiency, electricity_price)
    daily_cost = hourly_cost * 24
    attack_ths = attack_hashrate / 1e12
    hardware_cost = attack_ths * hardware_usd_per_th

    metric_cols = st.columns(5)
    metric_cols[0].metric("Network hash rate", _format_hashrate(network_hashrate))
    metric_cols[1].metric("51% hash rate", _format_hashrate(attack_hashrate))
    metric_cols[2].metric("Energy cost/hour", f"${hourly_cost:,.0f}")
    metric_cols[3].metric("Energy cost/day", f"${daily_cost:,.0f}")
    metric_cols[4].metric("Hardware scale", f"${hardware_cost:,.0f}")

    st.subheader("51% Attack Cost Assumptions")
    st.code(
        f"average block time window = {average_seconds:.1f} seconds\n"
        f"hashrate = difficulty * 2^32 / average_block_time\n"
        f"attacker hash rate = live network hash rate * 1.01\n"
        f"power (W) = TH/s * ASIC efficiency (J/TH)\n"
        f"hourly energy cost = kW * USD/kWh",
        language="text",
    )

    st.subheader("Confirmation Depth Risk")
    risk_rows = [
        {
            "Confirmations": confirmations,
            "Catch-up probability": _catch_up_probability(confirmations, attacker_share),
        }
        for confirmations in range(1, 13)
    ]
    risk_df = pd.DataFrame(risk_rows)
    risk_fig = px.line(
        risk_df,
        x="Confirmations",
        y="Catch-up probability",
        markers=True,
        title="Approximate Double-Spend Catch-Up Probability",
        labels={"Catch-up probability": "Probability"},
    )
    risk_fig.update_yaxes(tickformat=".2%")
    st.plotly_chart(risk_fig, width="stretch")

    st.dataframe(
        risk_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Catch-up probability": st.column_config.NumberColumn(format="%.6f"),
        },
    )

    st.caption(
        "The hardware scale is a rough capital estimate, while the hourly value is "
        "only the electricity cost. Real attacks also require logistics, pool "
        "coordination, opportunity cost, and market constraints."
    )
