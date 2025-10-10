"""Streamlit app for importing, classifying, and analysing basketball shots."""
from __future__ import annotations

from pathlib import Path
import sys
from typing import Any, Dict, Iterable, List, Literal

import pandas as pd
import streamlit as st
from PIL import Image

# Ensure local modules are importable when Streamlit adjusts the working directory.
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

try:
    import matplotlib.pyplot as plt
except ModuleNotFoundError:
    st.error(
        "matplotlib が必要です。環境にインストールされていない場合は `pip install matplotlib` を実行してください。"
    )
    st.stop()

from components import render_manual_counter, sidebar_filters
from storage import normalize_columns, read_csv, write_csv
from zone import ZONE_LABELS, Zone, classify_point, load_default_zones

st.set_page_config(page_title="バスケ シュート集計", layout="wide")
st.title("🏀 シュートエリア集計アプリ")


def init_session_state(zones: Iterable[Zone]) -> None:
    """Ensure session_state holds persistent data structures for CSV workflow."""

    if "zones" not in st.session_state:
        st.session_state["zones"] = list(zones)
    if "shots" not in st.session_state:
        st.session_state["shots"] = pd.DataFrame(columns=["x", "y", "result", "zone"])
    if "uploaded_df" not in st.session_state:
        st.session_state["uploaded_df"] = None
    if "column_mapping" not in st.session_state:
        st.session_state["column_mapping"] = {}


def _fresh_manual_counts() -> Dict[str, Dict[str, int]]:
    """Return a zero-initialised manual count structure."""

    return {label: {"make": 0, "miss": 0} for label in ZONE_LABELS}


def init_manual_counts(force: bool = False) -> None:
    """Initialise or reset manual tally counters stored in session_state."""

    if force or "manual_counts" not in st.session_state:
        st.session_state["manual_counts"] = _fresh_manual_counts()
        return

    counts = st.session_state["manual_counts"]
    for label in ZONE_LABELS:
        zone_counts = counts.get(label)
        if zone_counts is None or not {"make", "miss"}.issubset(zone_counts):
            counts[label] = {"make": 0, "miss": 0}


def increment_count(zone: str, outcome: Literal["make", "miss"]) -> None:
    """Increment the specified counter for a zone."""

    if zone not in ZONE_LABELS:
        raise ValueError(f"Unknown zone '{zone}'.")
    if outcome not in {"make", "miss"}:
        raise ValueError(f"Unknown outcome '{outcome}'.")

    init_manual_counts()
    st.session_state["manual_counts"][zone][outcome] += 1


def get_manual_summary_df() -> pd.DataFrame:
    """Aggregate manual tallies into a summary dataframe with totals."""

    init_manual_counts()
    counts = st.session_state["manual_counts"]
    records: List[Dict[str, Any]] = []
    total_make = 0
    total_miss = 0

    for zone in ZONE_LABELS:
        zone_counts = counts.get(zone, {"make": 0, "miss": 0})
        make_value = int(zone_counts.get("make", 0))
        miss_value = int(zone_counts.get("miss", 0))
        attempts = make_value + miss_value
        fg_pct = 0.0 if attempts == 0 else make_value / attempts * 100

        records.append(
            {
                "Zone": zone,
                "Make": make_value,
                "Miss": miss_value,
                "Attempts": attempts,
                "FG%": f"{fg_pct:.1f}%",
            }
        )
        total_make += make_value
        total_miss += miss_value

    total_attempts = total_make + total_miss
    total_pct = 0.0 if total_attempts == 0 else total_make / total_attempts * 100
    records.append(
        {
            "Zone": "TOTAL",
            "Make": total_make,
            "Miss": total_miss,
            "Attempts": total_attempts,
            "FG%": f"{total_pct:.1f}%",
        }
    )

    return pd.DataFrame.from_records(records)


def create_demo_dataframe() -> pd.DataFrame:
    """Return a small demo dataset to drive the import workflow."""

    return pd.DataFrame(
        {
            "shot_x": [180, 240, 360, 520, 140],
            "shot_y": [80, 200, 140, 320, 400],
            "PlayerName": ["Alice", "Alice", "Bob", "Charlie", "Charlie"],
            "period_no": [1, 2, 1, 2, 3],
            "make_flag": ["make", "miss", "make", "miss", "make"],
        }
    )


def apply_filters(df: pd.DataFrame, filters: Dict[str, List[Any]]) -> pd.DataFrame:
    """Filter the dataframe based on sidebar selections."""

    filtered = df.copy()
    for column, selected in filters.items():
        if column not in filtered.columns or not selected:
            continue
        filtered = filtered[filtered[column].isin(selected)]
    return filtered


def classify_dataframe(df: pd.DataFrame, zones: Iterable[Zone]) -> pd.DataFrame:
    """Append a zone column by running each row through classify_point."""

    classified = df.copy()
    classified["zone"] = [
        classify_point(float(row["x"]), float(row["y"]), zones)
        for _, row in classified.iterrows()
    ]
    return classified


def render_page_a(zones: Iterable[Zone]) -> None:
    """Render CSV import, mapping, classification, and download workflow."""

    st.subheader("Page A: CSV取り込みとエリア分類")
    st.write("CSVをアップロードし、列をマッピングしてゾーン分類を行います。")

    uploaded_file = st.file_uploader("CSVファイル", type=["csv"])

    if uploaded_file is not None:
        try:
            dataframe = read_csv(uploaded_file)
        except Exception as exc:  # pragma: no cover - Streamlit runtime feedback
            st.error(f"読み込みエラー: {exc}")
        else:
            st.session_state["uploaded_df"] = dataframe
            st.session_state["column_mapping"] = {}
            st.success("CSVを読み込みました。下で列マッピングを行ってください。")

    if st.button("デモ用データで試す"):
        demo_df = create_demo_dataframe()
        st.session_state["uploaded_df"] = demo_df
        st.session_state["column_mapping"] = {
            "x": "shot_x",
            "y": "shot_y",
            "result": "make_flag",
            "player": "PlayerName",
            "period": "period_no",
        }
        st.info("デモデータをロードしました。列マッピングを確認してください。")

    source_df = st.session_state.get("uploaded_df")
    if source_df is None:
        st.warning("CSVをアップロードするか、デモデータを使用してください。")
        return

    st.markdown("#### 取り込みデータのプレビュー")
    st.dataframe(source_df.head())

    required_targets = ("x", "y", "result")
    optional_targets = ("player", "period")

    with st.form("column_mapping_form"):
        st.markdown("#### 列名マッピング")
        mapping: Dict[str, str] = {}
        columns = source_df.columns.tolist()

        for target in required_targets:
            default = st.session_state["column_mapping"].get(target)
            if default not in columns:
                default = columns[0]
            index = columns.index(default)
            mapping[target] = st.selectbox(
                f"{target} 列", columns, index=index, key=f"map_req_{target}"
            )

        for target in optional_targets:
            options = ["--なし--"] + columns
            default = st.session_state["column_mapping"].get(target, "--なし--")
            if default not in options:
                default = "--なし--"
            index = options.index(default)
            selected = st.selectbox(
                f"{target} 列 (任意)", options, index=index, key=f"map_opt_{target}"
            )
            if selected != "--なし--":
                mapping[target] = selected

        submitted = st.form_submit_button("分類を実行")

    if submitted:
        st.session_state["column_mapping"] = mapping
        try:
            normalized = normalize_columns(source_df, mapping)
        except ValueError as exc:
            st.error(f"マッピングエラー: {exc}")
            return

        classified = classify_dataframe(normalized, zones)
        st.session_state["shots"] = classified
        st.success("ゾーン分類が完了しました。Page Bで集計を確認できます。")

    if st.session_state["shots"].empty:
        st.info("分類済みデータがありません。列マッピングを完了してください。")
        return

    st.markdown("#### 分類済みデータのプレビュー")
    st.dataframe(st.session_state["shots"].head())

    st.caption("zone 列が分類結果として追加されています。")

    st.download_button(
        label="分類済みCSVをダウンロード",
        data=write_csv(st.session_state["shots"]),
        file_name="shots_with_zones.csv",
        mime="text/csv",
    )


def render_page_b(filters: Dict[str, List[Any]]) -> None:
    """Render scatter plot and zone level summary on court image."""

    st.subheader("Page B: コート表示と集計")
    shots_df: pd.DataFrame = st.session_state["shots"]

    if shots_df.empty:
        st.warning("Page Aでデータを分類すると可視化できます。")
        return

    filtered_df = apply_filters(shots_df, filters)
    if filtered_df.empty:
        st.warning("選択されたフィルタに一致するデータがありません。")
        return

    try:
        court_image = Image.open("court.png")
    except FileNotFoundError:
        st.error("court.png が見つかりません。アプリと同じディレクトリに配置してください。")
        return

    width, height = court_image.size

    make_df = filtered_df[filtered_df["result"] == "MAKE"]
    miss_df = filtered_df[filtered_df["result"] == "MISS"]

    fig, ax = plt.subplots(figsize=(6, 8))
    ax.imshow(court_image, extent=[0, width, height, 0])

    if not make_df.empty:
        ax.scatter(make_df["x"], make_df["y"], c="tab:green", label="MAKE", marker="o")
    if not miss_df.empty:
        ax.scatter(
            miss_df["x"],
            miss_df["y"],
            c="tab:red",
            label="MISS",
            marker="x",
            alpha=0.7,
        )

    ax.set_xlim(0, width)
    ax.set_ylim(height, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.legend()
    ax.set_title("Shot Chart")

    st.pyplot(fig)
    plt.close(fig)

    summary = filtered_df.groupby("zone").agg(
        attempts=("result", "count"),
        makes=("result", lambda s: (s == "MAKE").sum()),
    )
    summary["FG%"] = (summary["makes"] / summary["attempts"] * 100).round(1)
    summary = summary.sort_values("attempts", ascending=False)

    st.markdown("#### エリア別集計")
    st.dataframe(summary)

    st.markdown("#### フィルタ後データ")
    st.dataframe(filtered_df)


def render_manual_tally() -> None:
    """Render manual tally interface for quick counting by zone."""

    init_manual_counts()

    st.subheader("Manual Tally: エリア別手動カウント")
    st.caption("成功・失敗ボタンで各エリアのカウントを更新します。")

    try:
        court_image = Image.open("court.png")
    except FileNotFoundError:
        st.error("court.png が見つかりません。アプリと同じディレクトリに配置してください。")
    else:
        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(court_image, use_column_width=True)

    counts = st.session_state["manual_counts"]
    columns = st.columns(len(ZONE_LABELS))
    for column, zone in zip(columns, ZONE_LABELS):
        with column:
            render_manual_counter(
                zone_name=zone,
                counts=counts.get(zone, {"make": 0, "miss": 0}),
                on_make=lambda z=zone: increment_count(z, "make"),
                on_miss=lambda z=zone: increment_count(z, "miss"),
            )

    st.divider()
    st.button(
        "すべてリセット",
        key="manual_counts_reset",
        on_click=init_manual_counts,
        kwargs={"force": True},
    )


def render_manual_summary() -> None:
    """Display manual tally results in a tabular summary."""

    st.subheader("Manual Summary: 手動集計結果")
    summary_df = get_manual_summary_df()
    st.table(summary_df.set_index("Zone"))


def main() -> None:
    """Application entry point."""

    zones = get_default_zones()
    init_session_state(zones)
    init_manual_counts()

    filters = sidebar_filters(st.session_state["shots"])
    page = st.selectbox(
        "表示ページ",
        ("Page A", "Page B", "Manual Tally", "Manual Summary"),
    )

    if page == "Page A":
        render_page_a(st.session_state["zones"])
    elif page == "Page B":
        render_page_b(filters)
    elif page == "Manual Tally":
        render_manual_tally()
    else:
        render_manual_summary()


if __name__ == "__main__":
    main()
