import math
import pandas as pd
import numpy as np
import streamlit as st
from PIL import Image
import streamlit_image_coordinates as stic

# ------------------------------------------------------
# ページ設定
# ------------------------------------------------------
st.set_page_config(page_title="バスケ シュート集計", layout="wide")
st.title("🏀 シュートエリア集計アプリ（クリックで記録）")

# ------------------------------------------------------
# 定数設定（画像サイズとリング位置）
# ------------------------------------------------------
W, H = 600, 500
HOOP_X, HOOP_Y = W // 2, 60
RIM_R = 7
PAINT_W = 160
PAINT_H = 190
ARC_R = 237
CORNER_3_Y = HOOP_Y + 140

# ------------------------------------------------------
# ゾーン分類関数
# ------------------------------------------------------
def classify_zone(x, y):
    """クリック座標 (x, y) をゾーンに分類する"""
    d = math.hypot(x - HOOP_X, y - HOOP_Y)
    left = HOOP_X - PAINT_W // 2
    right = HOOP_X + PAINT_W // 2

    # コーナー3
    if (x <= left or x >= right) and (y >= CORNER_3_Y):
        return "3P"
    # アーク外
    if d >= ARC_R:
        return "3P"
    # ペイント内
    if (left <= x <= right) and (HOOP_Y <= y <= HOOP_Y + PAINT_H):
        return "2P_paint"
    # それ以外
    return "2P_mid"

# ------------------------------------------------------
# セッション状態（記録を保持）
# ------------------------------------------------------
if "shots" not in st.session_state:
    st.session_state.shots = pd.DataFrame(columns=["x", "y", "zone", "made"])

# ------------------------------------------------------
# サイドバー入力
# ------------------------------------------------------
st.sidebar.header("入力オプション")
made_next = st.sidebar.selectbox("次のクリック：成功/失敗", ["成功（Made）", "失敗（Miss）"])
made_flag = "成功" in made_next

# ------------------------------------------------------
# コート画像の読み込み
# ------------------------------------------------------
try:
    court_img = Image.open("court.png")
except FileNotFoundError:
    st.error("❌ court.png が見つかりません。アプリと同じフォルダに置いてください。")
    st.stop()

col_canvas, col_table = st.columns([3, 2])

# ------------------------------------------------------
# クリック処理部分
# ------------------------------------------------------
with col_canvas:
    st.subheader("コート画像をクリックして記録")
    coords = stic.streamlit_image_coordinates(court_img, key="court")

    if coords is not None:
        x, y = coords["x"], coords["y"]
        zone = classify_zone(x, y)
        # 連続クリック防止
        if st.session_state.shots.empty or (
            abs(st.session_state.shots.iloc[-1]["x"] - x) > 1 or
            abs(st.session_state.shots.iloc[-1]["y"] - y) > 1
        ):
            new_row = {"x": x, "y": y, "zone": zone, "made": made_flag}
            st.session_state.shots = pd.concat(
                [st.session_state.shots, pd.DataFrame([new_row])],
                ignore_index=True,
            )

    # 操作ボタン
    c1, c2, c3 = st.columns(3)
    if c1.button("直前の1本を取り消し"):
        if not st.session_state.shots.empty:
            st.session_state.shots = st.session_state.shots.iloc[:-1]
    if c2.button("全クリア"):
        st.session_state.shots = st.session_state.shots.iloc[0:0]
    if c3.download_button(
        "CSVダウンロード",
        data=st.session_state.shots.to_csv(index=False).encode("utf-8"),
        file_name="shots.csv",
        mime="text/csv",
    ):
        pass

# ------------------------------------------------------
# 集計表示
# ------------------------------------------------------
with col_table:
    st.subheader("ゾーン別 集計")
    if st.session_state.shots.empty:
        st.info("まだ記録がありません。コートをクリックしてください。")
    else:
        g = st.session_state.shots.groupby("zone").agg(
            attempts=("made", "count"),
            makes=("made", "sum"),
        )
        g["FG%"] = (g["makes"] / g["attempts"] * 100).round(1)
        st.dataframe(g.sort_values("attempts", ascending=False))

        st.subheader("全記録（最新が下）")
        st.dataframe(st.session_state.shots.tail(200))
