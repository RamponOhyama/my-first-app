import math
import numpy as np
import pandas as pd
import streamlit as st
from io import BytesIO
from PIL import Image, ImageDraw
from streamlit_drawable_canvas import st_canvas

# -----------------------------------
# ページ設定
# -----------------------------------
st.set_page_config(page_title="バスケ シュート集計", layout="wide")
st.title("🏀 シュートエリア集計アプリ（タップで記録）")

# -----------------------------------
# コート定義
# -----------------------------------
W, H = 600, 500
HOOP_X, HOOP_Y = W // 2, 60
RIM_R = 7
PAINT_W = 160
PAINT_H = 190
ARC_R = 237
CORNER_3_Y = HOOP_Y + 140

# -----------------------------------
# コート背景画像生成
# -----------------------------------
def make_court_image():
    img = Image.new("RGB", (W, H), (234, 179, 93))
    drw = ImageDraw.Draw(img)

    # ペイント
    left, right = HOOP_X - PAINT_W // 2, HOOP_X + PAINT_W // 2
    top, bottom = HOOP_Y, HOOP_Y + PAINT_H
    drw.rectangle([left, top, right, bottom], outline=(255, 255, 255), width=3)

    # リング
    drw.ellipse(
        [HOOP_X - RIM_R, HOOP_Y - RIM_R, HOOP_X + RIM_R, HOOP_Y + RIM_R],
        outline=(255, 80, 80), width=3,
    )

    # 3Pアーク
    bbox = [HOOP_X - ARC_R, HOOP_Y - ARC_R, HOOP_X + ARC_R, HOOP_Y + ARC_R]
    drw.arc(bbox, start=200, end=-20, fill=(255, 255, 255), width=3)

    # コーナー3P
    drw.line([(left, HOOP_Y), (left, CORNER_3_Y)], fill=(255, 255, 255), width=3)
    drw.line([(right, HOOP_Y), (right, CORNER_3_Y)], fill=(255, 255, 255), width=3)

    drw.text((10, 10), "タップで記録 / クリック位置を判定してゾーン集計", fill=(0, 0, 0))
    return img

# ✅ 修正済み：NumPy配列に変換して渡す（PILやBytesIOではなく）
bg_img_pil = make_court_image()
bg_img = np.array(bg_img_pil)

# -----------------------------------
# ゾーン判定
# -----------------------------------
def classify_zone(x, y):
    d = math.hypot(x - HOOP_X, y - HOOP_Y)
    left = HOOP_X - PAINT_W // 2
    right = HOOP_X + PAINT_W // 2

    if (x <= left or x >= right) and (y >= CORNER_3_Y):
        return "3P"
    if d >= ARC_R:
        return "3P"

    paint_top, paint_bottom = HOOP_Y, HOOP_Y + PAINT_H
    if (left <= x <= right) and (paint_top <= y <= paint_bottom):
        return "2P_paint"
    return "2P_mid"

# -----------------------------------
# セッション管理
# -----------------------------------
if "shots" not in st.session_state:
    st.session_state.shots = pd.DataFrame(columns=["x", "y", "zone", "made"])

st.sidebar.header("入力オプション")
made_next = st.sidebar.selectbox("次のタップ：成功/失敗", ["成功（Made）", "失敗（Miss）"])
made_flag = "成功" in made_next

col_canvas, col_table = st.columns([3, 2])

# -----------------------------------
# Canvas
# -----------------------------------
with col_canvas:
    st.subheader("コート（タップで記録）")
    canvas_result = st_canvas(
        fill_color="rgba(255, 0, 0, 0.6)",
        stroke_width=10,
        background_image=bg_img,  # ✅ NumPy配列で渡す
        update_streamlit=True,
        drawing_mode="point",
        width=W,
        height=H,
        key="court",
    )

    # クリック処理
    if canvas_result.json_data is not None:
        objs = canvas_result.json_data.get("objects", [])
        if len(objs) > 0:
            last = objs[-1]
            x = float(last.get("left", 0))
            y = float(last.get("top", 0))
            zone = classify_zone(x, y)
            if st.session_state.shots.empty or (
                abs(st.session_state.shots.iloc[-1]["x"] - x) > 1 or
                abs(st.session_state.shots.iloc[-1]["y"] - y) > 1
            ):
                new_row = {"x": x, "y": y, "zone": zone, "made": made_flag}
                st.session_state.shots = pd.concat(
                    [st.session_state.shots, pd.DataFrame([new_row])],
                    ignore_index=True,
                )

    # ボタン操作
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

# -----------------------------------
# 集計表示
# -----------------------------------
with col_table:
    st.subheader("ゾーン別 集計")
    if st.session_state.shots.empty:
        st.info("まだ記録がありません。コートをタップして記録してください。")
    else:
        g = st.session_state.shots.groupby("zone").agg(
            attempts=("made", "count"),
            makes=("made", "sum"),
        )
        g["FG%"] = (g["makes"] / g["attempts"] * 100).round(1)
        st.dataframe(g.sort_values("attempts", ascending=False))

        st.subheader("全記録（最新が下）")
        st.dataframe(st.session_state.shots.tail(200))
