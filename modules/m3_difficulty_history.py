"""Difficulty adjustment history dashboard module."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from api.blockchain_client import (
    get_blockstream_block_by_height,
    get_latest_block_height,
)

BLOCKS_PER_ADJUSTMENT = 2016
TARGET_BLOCK_TIME_SECONDS = 600
TARGET_PERIOD_SECONDS = BLOCKS_PER_ADJUSTMENT * TARGET_BLOCK_TIME_SECONDS


@st.cache_data(ttl=300)
def _load_adjustment_periods(period_count: int) -> tuple[int, list[dict]]:
    """Load completed difficulty adjustment periods from Blockstream."""
    tip_height = get_latest_block_height()
    last_boundary = tip_height - (tip_height % BLOCKS_PER_ADJUSTMENT)
    first_boundary = max(0, last_boundary - period_count * BLOCKS_PER_ADJUSTMENT)
    boundary_heights = list(
        range(first_boundary, last_boundary + BLOCKS_PER_ADJUSTMENT, BLOCKS_PER_ADJUSTMENT)
    )

    boundary_blocks = {
        height: get_blockstream_block_by_height(height) for height in boundary_heights
    }

    periods = []
    for start_height, end_boundary in zip(boundary_heights, boundary_heights[1:]):
        start_block = boundary_blocks[start_height]
        end_block = boundary_blocks[end_boundary]
        actual_seconds = end_block["timestamp"] - start_block["timestamp"]
        ratio = actual_seconds / TARGET_PERIOD_SECONDS
        expected_next_difficulty = start_block["difficulty"] / ratio

        periods.append(
            {
                "Period start height": start_height,
                "Period end height": end_boundary - 1,
                "Adjustment height": end_boundary,
                "Start date": pd.to_datetime(start_block["timestamp"], unit="s"),
                "Adjustment date": pd.to_datetime(end_block["timestamp"], unit="s"),
                "Difficulty": start_block["difficulty"],
                "Next difficulty": end_block["difficulty"],
                "Actual days": actual_seconds / 86400,
                "Target days": TARGET_PERIOD_SECONDS / 86400,
                "Actual/target ratio": ratio,
                "Retarget estimate": expected_next_difficulty,
                "Difficulty change %": (
                    (end_block["difficulty"] / start_block["difficulty"]) - 1
                )
                * 100,
            }
        )

    return tip_height, periods


def render() -> None:
    """Render the M3 panel."""
    st.header("M3 - Difficulty History")

    col_settings, col_refresh = st.columns([1, 2])
    with col_settings:
        period_count = st.slider(
            "Adjustment periods",
            min_value=3,
            max_value=12,
            value=8,
            key="m3_period_count",
        )
    with col_refresh:
        st.caption(
            "Each Bitcoin difficulty adjustment period contains 2016 blocks, "
            "with a target duration of 14 days."
        )
        if st.button("Refresh difficulty history", key="m3_refresh"):
            _load_adjustment_periods.clear()

    try:
        tip_height, periods = _load_adjustment_periods(period_count)
    except Exception as exc:
        st.error(f"Error loading difficulty history: {exc}")
        return

    if not periods:
        st.warning("Not enough data was returned to build the difficulty history.")
        return

    df = pd.DataFrame(periods)
    latest_period = df.iloc[-1]

    metric_cols = st.columns(4)
    metric_cols[0].metric("Current tip height", f"{tip_height:,}")
    metric_cols[1].metric("Latest period difficulty", f"{latest_period['Difficulty']:,.0f}")
    metric_cols[2].metric(
        "Latest actual/target",
        f"{latest_period['Actual/target ratio']:.3f}",
    )
    metric_cols[3].metric(
        "Latest change",
        f"{latest_period['Difficulty change %']:+.2f}%",
    )

    st.subheader("Difficulty at Adjustment Events")
    difficulty_fig = px.line(
        df,
        x="Start date",
        y="Difficulty",
        markers=True,
        title="Bitcoin Difficulty Over Recent Adjustment Periods",
        labels={
            "Start date": "Period start date",
            "Difficulty": "Difficulty",
        },
    )
    for _, row in df.iterrows():
        difficulty_fig.add_vline(
            x=row["Start date"],
            line_dash="dot",
            line_color="gray",
            opacity=0.35,
        )
    difficulty_fig.update_layout(yaxis_title="Difficulty")
    st.plotly_chart(difficulty_fig, width="stretch")

    st.subheader("Actual Block Time vs Target")
    ratio_fig = px.bar(
        df,
        x="Adjustment date",
        y="Actual/target ratio",
        title="Actual Period Duration Divided by 2016 x 600 Seconds",
        labels={
            "Adjustment date": "Adjustment date",
            "Actual/target ratio": "Actual duration / target duration",
        },
        hover_data={
            "Period start height": True,
            "Period end height": True,
            "Actual days": ":.2f",
            "Difficulty change %": ":.2f",
        },
    )
    ratio_fig.add_hline(
        y=1,
        line_dash="dash",
        line_color="red",
        annotation_text="target",
    )
    st.plotly_chart(ratio_fig, width="stretch")

    st.subheader("Adjustment Period Table")
    display_df = df[
        [
            "Period start height",
            "Period end height",
            "Adjustment height",
            "Start date",
            "Adjustment date",
            "Difficulty",
            "Next difficulty",
            "Actual days",
            "Actual/target ratio",
            "Difficulty change %",
        ]
    ].sort_values("Period start height", ascending=False)
    st.dataframe(
        display_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Difficulty": st.column_config.NumberColumn(format="%.0f"),
            "Next difficulty": st.column_config.NumberColumn(format="%.0f"),
            "Actual days": st.column_config.NumberColumn(format="%.2f"),
            "Actual/target ratio": st.column_config.NumberColumn(format="%.3f"),
            "Difficulty change %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )

    st.caption(
        "If the ratio is below 1, blocks arrived faster than the 10 minute target "
        "and the next difficulty should increase. If the ratio is above 1, blocks "
        "arrived slower and the next difficulty should decrease."
    )
