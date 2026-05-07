"""Second AI approach: Bitcoin difficulty adjustment predictor."""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_blockstream_block_by_height, get_latest_block_height

BLOCKS_PER_ADJUSTMENT = 2016
TARGET_BLOCK_TIME_SECONDS = 600
TARGET_PERIOD_SECONDS = BLOCKS_PER_ADJUSTMENT * TARGET_BLOCK_TIME_SECONDS


@st.cache_data(ttl=300)
def _load_period_dataset(period_count: int) -> tuple[int, pd.DataFrame, dict]:
    """Load completed periods and current incomplete-period context."""
    tip_height = get_latest_block_height()
    last_boundary = tip_height - (tip_height % BLOCKS_PER_ADJUSTMENT)
    first_boundary = max(0, last_boundary - period_count * BLOCKS_PER_ADJUSTMENT)
    boundary_heights = list(
        range(first_boundary, last_boundary + BLOCKS_PER_ADJUSTMENT, BLOCKS_PER_ADJUSTMENT)
    )

    boundary_blocks = {
        height: get_blockstream_block_by_height(height) for height in boundary_heights
    }

    rows = []
    previous_change_pct = 0.0
    for index, (start_height, next_boundary) in enumerate(
        zip(boundary_heights, boundary_heights[1:])
    ):
        start_block = boundary_blocks[start_height]
        next_block = boundary_blocks[next_boundary]
        actual_seconds = next_block["timestamp"] - start_block["timestamp"]
        ratio = actual_seconds / TARGET_PERIOD_SECONDS
        current_difficulty = start_block["difficulty"]
        next_difficulty = next_block["difficulty"]
        baseline_prediction = current_difficulty / ratio
        change_pct = ((next_difficulty / current_difficulty) - 1) * 100

        rows.append(
            {
                "Period index": index,
                "Start height": start_height,
                "Adjustment height": next_boundary,
                "Start date": pd.to_datetime(start_block["timestamp"], unit="s"),
                "Current difficulty": current_difficulty,
                "Actual/target ratio": ratio,
                "Previous change %": previous_change_pct,
                "Baseline prediction": baseline_prediction,
                "Actual next difficulty": next_difficulty,
                "Actual change %": change_pct,
            }
        )
        previous_change_pct = change_pct

    current_start_block = boundary_blocks[last_boundary]
    tip_block = get_blockstream_block_by_height(tip_height)
    elapsed_blocks = max(1, tip_height - last_boundary)
    elapsed_seconds = max(1, tip_block["timestamp"] - current_start_block["timestamp"])
    average_so_far = elapsed_seconds / elapsed_blocks
    projected_ratio = (average_so_far * BLOCKS_PER_ADJUSTMENT) / TARGET_PERIOD_SECONDS
    current_context = {
        "Start height": last_boundary,
        "Tip height": tip_height,
        "Elapsed blocks": elapsed_blocks,
        "Current difficulty": current_start_block["difficulty"],
        "Projected actual/target ratio": projected_ratio,
        "Previous change %": previous_change_pct,
        "Baseline prediction": current_start_block["difficulty"] / projected_ratio,
    }

    return tip_height, pd.DataFrame(rows), current_context


def _feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Build model features for difficulty prediction."""
    return np.column_stack(
        [
            np.ones(len(df)),
            df["Current difficulty"].to_numpy(dtype=float),
            df["Actual/target ratio"].to_numpy(dtype=float),
            df["Previous change %"].to_numpy(dtype=float),
        ]
    )


def _fit_linear_model(train_df: pd.DataFrame) -> np.ndarray:
    features = _feature_matrix(train_df)
    target = train_df["Actual next difficulty"].to_numpy(dtype=float)
    coefficients, *_ = np.linalg.lstsq(features, target, rcond=None)
    return coefficients


def _predict(coefficients: np.ndarray, df: pd.DataFrame) -> np.ndarray:
    return _feature_matrix(df) @ coefficients


def _mae(actual: pd.Series, predicted: np.ndarray) -> float:
    return float(np.abs(actual.to_numpy(dtype=float) - predicted).mean())


def _mape(actual: pd.Series, predicted: np.ndarray) -> float:
    actual_values = actual.to_numpy(dtype=float)
    return float((np.abs((actual_values - predicted) / actual_values)).mean() * 100)


def render() -> None:
    """Render the M7 panel."""
    st.header("M7 - Second AI Approach")
    st.subheader("Difficulty Adjustment Predictor")

    settings_col, info_col = st.columns([1, 2])
    with settings_col:
        period_count = st.slider(
            "Historical periods",
            min_value=8,
            max_value=24,
            value=14,
            step=2,
            key="m7_period_count",
        )
        if st.button("Refresh predictor data", key="m7_refresh"):
            _load_period_dataset.clear()
    with info_col:
        st.caption(
            "This second AI method uses linear regression to predict the next "
            "difficulty adjustment from recent 2016-block period features."
        )

    try:
        tip_height, df, current_context = _load_period_dataset(period_count)
    except Exception as exc:
        st.error(f"Error loading predictor data: {exc}")
        return

    if len(df) < 8:
        st.warning("Not enough completed adjustment periods to train the predictor.")
        return

    split_index = max(5, int(len(df) * 0.7))
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:].copy()

    coefficients = _fit_linear_model(train_df)
    regression_predictions = _predict(coefficients, test_df)
    baseline_predictions = test_df["Baseline prediction"].to_numpy(dtype=float)

    test_df["Regression prediction"] = regression_predictions
    test_df["Regression error %"] = (
        (test_df["Regression prediction"] - test_df["Actual next difficulty"])
        / test_df["Actual next difficulty"]
    ) * 100
    test_df["Baseline error %"] = (
        (test_df["Baseline prediction"] - test_df["Actual next difficulty"])
        / test_df["Actual next difficulty"]
    ) * 100

    regression_mae = _mae(test_df["Actual next difficulty"], regression_predictions)
    regression_mape = _mape(test_df["Actual next difficulty"], regression_predictions)
    baseline_mae = _mae(test_df["Actual next difficulty"], baseline_predictions)
    baseline_mape = _mape(test_df["Actual next difficulty"], baseline_predictions)

    current_row = pd.DataFrame(
        [
            {
                "Current difficulty": current_context["Current difficulty"],
                "Actual/target ratio": current_context["Projected actual/target ratio"],
                "Previous change %": current_context["Previous change %"],
            }
        ]
    )
    next_prediction = float(_predict(coefficients, current_row)[0])

    metric_cols = st.columns(5)
    metric_cols[0].metric("Tip height", f"{tip_height:,}")
    metric_cols[1].metric("Train periods", len(train_df))
    metric_cols[2].metric("Test periods", len(test_df))
    metric_cols[3].metric("Regression MAPE", f"{regression_mape:.2f}%")
    metric_cols[4].metric("Predicted next difficulty", f"{next_prediction:,.0f}")

    st.subheader("Evaluation Against Baseline")
    evaluation_df = pd.DataFrame(
        [
            {
                "Model": "Linear regression",
                "MAE": regression_mae,
                "MAPE %": regression_mape,
            },
            {
                "Model": "Protocol-formula baseline",
                "MAE": baseline_mae,
                "MAPE %": baseline_mape,
            },
        ]
    )
    st.dataframe(
        evaluation_df,
        width="stretch",
        hide_index=True,
        column_config={
            "MAE": st.column_config.NumberColumn(format="%.0f"),
            "MAPE %": st.column_config.NumberColumn(format="%.2f"),
        },
    )

    st.subheader("Predictions on Test Periods")
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=test_df["Adjustment height"],
            y=test_df["Actual next difficulty"],
            mode="lines+markers",
            name="Actual",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=test_df["Adjustment height"],
            y=test_df["Regression prediction"],
            mode="lines+markers",
            name="Linear regression",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=test_df["Adjustment height"],
            y=test_df["Baseline prediction"],
            mode="lines+markers",
            name="Baseline",
        )
    )
    fig.update_layout(
        title="Difficulty Prediction: Actual vs Models",
        xaxis_title="Adjustment height",
        yaxis_title="Difficulty",
    )
    st.plotly_chart(fig, width="stretch")

    st.dataframe(
        test_df[
            [
                "Adjustment height",
                "Actual/target ratio",
                "Actual next difficulty",
                "Regression prediction",
                "Regression error %",
                "Baseline prediction",
                "Baseline error %",
            ]
        ].sort_values("Adjustment height", ascending=False),
        width="stretch",
        hide_index=True,
        column_config={
            "Actual/target ratio": st.column_config.NumberColumn(format="%.3f"),
            "Actual next difficulty": st.column_config.NumberColumn(format="%.0f"),
            "Regression prediction": st.column_config.NumberColumn(format="%.0f"),
            "Regression error %": st.column_config.NumberColumn(format="%+.2f%%"),
            "Baseline prediction": st.column_config.NumberColumn(format="%.0f"),
            "Baseline error %": st.column_config.NumberColumn(format="%+.2f%%"),
        },
    )

    st.subheader("Current Period Forecast")
    st.code(
        f"current period start height = {current_context['Start height']}\n"
        f"current tip height          = {current_context['Tip height']}\n"
        f"elapsed blocks              = {current_context['Elapsed blocks']}\n"
        f"projected actual/target     = {current_context['Projected actual/target ratio']:.3f}\n"
        f"baseline prediction         = {current_context['Baseline prediction']:,.0f}\n"
        f"linear regression prediction = {next_prediction:,.0f}",
        language="text",
    )

    st.caption(
        "This model is intentionally simple and explainable. It is not a trading "
        "or mining recommendation; it demonstrates a second AI-style prediction "
        "pipeline trained and evaluated on real blockchain data."
    )
