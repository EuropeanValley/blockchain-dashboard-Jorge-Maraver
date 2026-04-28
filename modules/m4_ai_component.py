"""AI component: anomaly detection for Bitcoin inter-block times."""

from __future__ import annotations

import math

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from api.blockchain_client import get_recent_blocks


@st.cache_data(ttl=300)
def _load_blocks(n_blocks: int) -> list[dict]:
    return get_recent_blocks(n_blocks)


def _build_interval_dataframe(blocks: list[dict]) -> pd.DataFrame:
    """Return oldest-to-newest inter-block times."""
    ordered_blocks = sorted(blocks, key=lambda block: block["height"])
    rows = []
    for previous, current in zip(ordered_blocks, ordered_blocks[1:]):
        seconds = current["timestamp"] - previous["timestamp"]
        if seconds <= 0:
            continue
        rows.append(
            {
                "Height": current["height"],
                "Block hash": current["id"],
                "Timestamp": pd.to_datetime(current["timestamp"], unit="s"),
                "Inter-block time (s)": seconds,
                "Inter-block time (min)": seconds / 60,
                "Tx count": current["tx_count"],
                "Difficulty": current["difficulty"],
            }
        )
    return pd.DataFrame(rows)


def _fit_exponential_mean(values: pd.Series) -> float:
    """Fit an exponential distribution by maximum likelihood."""
    return float(values.mean())


def _exponential_cdf(value: float, mean_seconds: float) -> float:
    return 1 - math.exp(-value / mean_seconds)


def _two_sided_p_value(value: float, mean_seconds: float) -> float:
    lower_tail = _exponential_cdf(value, mean_seconds)
    upper_tail = math.exp(-value / mean_seconds)
    return min(1.0, 2 * min(lower_tail, upper_tail))


def _ks_statistic(values: pd.Series, mean_seconds: float) -> float:
    """Compute a simple one-sample KS statistic against the fitted exponential."""
    sorted_values = sorted(float(value) for value in values)
    n_values = len(sorted_values)
    if n_values == 0:
        return 0.0

    distances = []
    for index, value in enumerate(sorted_values, start=1):
        cdf = _exponential_cdf(value, mean_seconds)
        empirical_upper = index / n_values
        empirical_lower = (index - 1) / n_values
        distances.append(max(abs(empirical_upper - cdf), abs(cdf - empirical_lower)))
    return max(distances)


def _negative_log_likelihood(values: pd.Series, mean_seconds: float) -> float:
    """Return average negative log-likelihood under the exponential model."""
    return float((math.log(mean_seconds) + values / mean_seconds).mean())


def _score_intervals(df: pd.DataFrame, mean_seconds: float, alpha: float) -> pd.DataFrame:
    scored = df.copy()
    scored["Expected mean (s)"] = mean_seconds
    scored["Two-sided p-value"] = scored["Inter-block time (s)"].apply(
        lambda value: _two_sided_p_value(float(value), mean_seconds)
    )
    scored["Anomaly"] = scored["Two-sided p-value"] < alpha
    scored["Anomaly type"] = scored["Inter-block time (s)"].apply(
        lambda value: "Fast" if value < mean_seconds else "Slow"
    )
    return scored


def _histogram_with_exponential(scored_df: pd.DataFrame, mean_seconds: float) -> go.Figure:
    values = scored_df["Inter-block time (s)"]
    max_value = max(float(values.max()), mean_seconds * 4)
    bin_count = 24
    bin_width = max_value / bin_count
    x_values = [index * bin_width for index in range(bin_count + 1)]
    y_values = [
        len(values) * bin_width * (1 / mean_seconds) * math.exp(-x / mean_seconds)
        for x in x_values
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Histogram(
            x=values,
            nbinsx=bin_count,
            name="Observed intervals",
            opacity=0.75,
        )
    )
    fig.add_trace(
        go.Scatter(
            x=x_values,
            y=y_values,
            mode="lines",
            name="Expected exponential baseline",
        )
    )
    fig.update_layout(
        title="Observed Inter-Block Times vs Exponential Baseline",
        xaxis_title="Seconds between blocks",
        yaxis_title="Number of blocks",
        bargap=0.05,
    )
    return fig


def _timeline(scored_df: pd.DataFrame) -> go.Figure:
    normal = scored_df[~scored_df["Anomaly"]]
    anomalies = scored_df[scored_df["Anomaly"]]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=normal["Timestamp"],
            y=normal["Inter-block time (s)"],
            mode="markers",
            name="Normal",
            marker={"size": 8},
            text=normal["Height"],
            hovertemplate="Height %{text}<br>%{y:.0f}s<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=anomalies["Timestamp"],
            y=anomalies["Inter-block time (s)"],
            mode="markers",
            name="Anomaly",
            marker={"size": 11, "color": "crimson", "symbol": "diamond"},
            text=anomalies["Height"],
            hovertemplate="Height %{text}<br>%{y:.0f}s<extra></extra>",
        )
    )
    fig.add_hline(
        y=600,
        line_dash="dash",
        line_color="red",
        annotation_text="10 min target",
    )
    fig.update_layout(
        title="Anomaly Detection Timeline",
        xaxis_title="Block timestamp",
        yaxis_title="Seconds since previous block",
    )
    return fig


def render() -> None:
    """Render the M4 panel."""
    st.header("M4 - AI Component")
    st.subheader("Anomaly Detector for Bitcoin Inter-Block Times")

    settings_col, info_col = st.columns([1, 2])
    with settings_col:
        n_blocks = st.slider(
            "Recent blocks",
            min_value=80,
            max_value=300,
            value=160,
            step=20,
            key="m4_n_blocks",
        )
        alpha = st.slider(
            "Anomaly p-value threshold",
            min_value=0.01,
            max_value=0.20,
            value=0.05,
            step=0.01,
            key="m4_alpha",
        )
    with info_col:
        st.caption(
            "Model choice: an exponential baseline for block waiting times. "
            "Bitcoin mining is approximately a Poisson process, so the waiting "
            "time between blocks is expected to follow an exponential distribution."
        )
        if st.button("Refresh AI data", key="m4_refresh"):
            _load_blocks.clear()

    try:
        blocks = _load_blocks(n_blocks)
    except Exception as exc:
        st.error(f"Error loading block data for AI module: {exc}")
        return

    df = _build_interval_dataframe(blocks)
    if len(df) < 30:
        st.warning("Not enough inter-block intervals were returned to train the model.")
        return

    split_index = max(20, int(len(df) * 0.7))
    train_df = df.iloc[:split_index]
    test_df = df.iloc[split_index:]

    mean_seconds = _fit_exponential_mean(train_df["Inter-block time (s)"])
    scored_df = _score_intervals(df, mean_seconds, alpha)
    scored_test_df = _score_intervals(test_df, mean_seconds, alpha)

    ks_train = _ks_statistic(train_df["Inter-block time (s)"], mean_seconds)
    ks_test = _ks_statistic(test_df["Inter-block time (s)"], mean_seconds)
    nll_test = _negative_log_likelihood(test_df["Inter-block time (s)"], mean_seconds)
    anomaly_rate = float(scored_test_df["Anomaly"].mean())

    metric_cols = st.columns(5)
    metric_cols[0].metric("Training intervals", len(train_df))
    metric_cols[1].metric("Test intervals", len(test_df))
    metric_cols[2].metric("Fitted mean", f"{mean_seconds:.1f} s")
    metric_cols[3].metric("Test anomaly rate", f"{anomaly_rate * 100:.1f}%")
    metric_cols[4].metric("Test KS statistic", f"{ks_test:.3f}")

    st.subheader("Model Evaluation")
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Metric": "Train KS statistic",
                    "Value": ks_train,
                    "Meaning": "Lower means the training data is closer to the exponential baseline.",
                },
                {
                    "Metric": "Test KS statistic",
                    "Value": ks_test,
                    "Meaning": "Out-of-sample distribution fit against the exponential baseline.",
                },
                {
                    "Metric": "Test negative log-likelihood",
                    "Value": nll_test,
                    "Meaning": "Lower means the model assigns higher probability to test intervals.",
                },
                {
                    "Metric": "Test anomaly rate",
                    "Value": anomaly_rate,
                    "Meaning": "Share of test intervals below the selected p-value threshold.",
                },
            ]
        ),
        width="stretch",
        hide_index=True,
        column_config={"Value": st.column_config.NumberColumn(format="%.4f")},
    )

    st.plotly_chart(_timeline(scored_df), width="stretch")
    st.plotly_chart(_histogram_with_exponential(scored_df, mean_seconds), width="stretch")

    st.subheader("Detected Anomalies")
    anomalies = scored_df[scored_df["Anomaly"]].sort_values(
        "Two-sided p-value", ascending=True
    )
    if anomalies.empty:
        st.info("No anomalies found with the current threshold.")
    else:
        st.dataframe(
            anomalies[
                [
                    "Height",
                    "Timestamp",
                    "Inter-block time (s)",
                    "Inter-block time (min)",
                    "Anomaly type",
                    "Two-sided p-value",
                    "Tx count",
                ]
            ],
            width="stretch",
            hide_index=True,
            column_config={
                "Inter-block time (s)": st.column_config.NumberColumn(format="%.0f"),
                "Inter-block time (min)": st.column_config.NumberColumn(format="%.2f"),
                "Two-sided p-value": st.column_config.NumberColumn(format="%.5f"),
            },
        )

    st.caption(
        "This detector is unsupervised: there are no ground-truth anomaly labels. "
        "The evaluation therefore measures distribution fit and out-of-sample "
        "likelihood instead of accuracy or F1."
    )
