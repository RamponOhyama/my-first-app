"""Reusable Streamlit UI components."""
from __future__ import annotations

from typing import Any, Callable, Dict, List

import pandas as pd
import streamlit as st


FILTER_ORDER = ("player", "period", "zone", "result")


def sidebar_filters(df: pd.DataFrame) -> Dict[str, List[Any]]:
    """Render sidebar filters and return selected values for each column."""

    filters: Dict[str, List[Any]] = {}
    if df.empty:
        st.sidebar.info("データを読み込むとフィルタが利用できます。")
        return filters

    st.sidebar.header("フィルタ")
    for column in FILTER_ORDER:
        if column not in df.columns:
            continue
        options = sorted(df[column].dropna().unique().tolist())
        if not options:
            continue
        default = options
        label = column.capitalize()
        filters[column] = st.sidebar.multiselect(label, options, default=default)

    return filters


def render_manual_counter(
    zone_name: str,
    counts: Dict[str, int],
    on_make: Callable[[], None],
    on_miss: Callable[[], None],
) -> None:
    """Display a manual tally card with counters and increment buttons."""

    make_value = counts.get("make", 0)
    miss_value = counts.get("miss", 0)

    with st.container():
        st.markdown(f"#### {zone_name}")
        col_make, col_miss = st.columns(2)
        col_make.metric("成功", make_value)
        col_miss.metric("失敗", miss_value)

        btn_col_make, btn_col_miss = st.columns(2)
        btn_col_make.button(
            "成功（+1）",
            key=f"{zone_name}_make_button",
            on_click=on_make,
        )
        btn_col_miss.button(
            "失敗（+1）",
            key=f"{zone_name}_miss_button",
            on_click=on_miss,
        )
