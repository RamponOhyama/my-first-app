"""Reusable Streamlit UI components."""
from __future__ import annotations

from typing import Any, Dict, List

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
