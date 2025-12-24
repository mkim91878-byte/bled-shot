# main.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from pathlib import Path
import unicodedata
import io

# ==================================================
# 기본 설정
# ==================================================
st.set_page_config(
    page_title="극지식물 최적 EC 농도 연구",
    layout="wide"
)

# ==================================================
# 한글 폰트 깨짐 방지 (Streamlit)
# ==================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR&display=swap');
html, body, [class*="css"] {
    font-family: 'Noto Sans KR', 'Malgun Gothic', sans-serif;
}
</style>
""", unsafe_allow_html=True)

PLOTLY_FONT = dict(
    family="Malgun Gothic, Apple SD Gothic Neo, sans-serif"
)

# ==================================================
# 경로 설정
# ==================================================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

# ==================================================
# NFC / NFD 안전 파일 탐색
# ==================================================
def find_file_by_name(directory: Path, target_name: str):
    target_nfc = unicodedata.normalize("NFC", target_name)
    target_nfd = unicodedata.normalize("NFD", target_name)

    for p in directory.iterdir():
        if not p.is_file():
            continue

        name_nfc = unicodedata.normalize("NFC", p.name)
        name_nfd = unicodedata.normalize("NFD", p.name)

        if name_nfc == target_nfc or name_nfd == target_nfd:
            return p
    return None

# ==================================================
# 데이터 로딩 (캐시)
# ==================================================
@st.cache_data
def load_environment_data():
    env = {}
    for f in DATA_DIR.iterdir():
        if f.suffix.lower() != ".csv":
            continue
        school = f.stem.replace("_환경데이터", "")
        df = pd.read_csv(f)
        df["school"] = school
        env[school] = df

    if not env:
        st.error("환경 데이터 CSV 파일을 찾을 수 없습니다.")
        return None

    return env


@st.cache_data
def load_growth_data():
    xlsx = find_file_by_name(DATA_DIR, "4개교_생육결과데이터.xlsx")
    if xlsx is None:
        st.error("생육 결과 XLSX 파일을 찾을 수 없습니다.")
        return None

    excel = pd.ExcelFile(xlsx)
    growth = {}

    for sheet in excel.sheet_names:
        df = pd.read_excel(xlsx, sheet_name=sheet)
        df["school"] = sheet
        growth[sheet] = df

    return growth

# ==================================================
# EC 정보
# ==================================================
EC_INFO = {
    "송도고": 1.0,
    "하늘고": 2.0,  # 최적
    "아라고": 4.0,
    "동산고": 8.0,
}

# ==================================================
# 데이터 로딩
# ==================================================
with st.spinner("데이터 로딩 중..."):
    env_data = load_environment_data()
    growth_data = load_growth_data()

if env_data is None or growth_data is None:
    st.stop()

# ==================================================
# 사이드바
# ==================================================
st.sidebar.title("학교 선택")
school_options = ["전체"] + list(EC_INFO.keys())
selected_school = st.sidebar.selectbox("학교", school_options)

# ==================================================
# 제목
# ==================================================
st.title("🌱 극지식물 최적 EC 농도 연구")

tab1, tab2, tab3 = st.tabs(["📖 실험 개요", "🌡️ 환경 데이터", "📊 생육 결과"])

# ==================================================
# Tab 1: 실험 개요
# ==================================================
with tab1:
    st.subheader("연구 배경 및 목적")
    st.write(
        "본 연구는 4개 학교의 실험 데이터를 활용하여 "
        "극지식물 생육에 최적인 EC 농도를 도출하는 것을 목표로 한다."
    )

    rows = []
    total = 0
    for school, ec in EC_INFO.items():
        count = len(growth_data.get(school, []))
        total += count
        rows.append({
            "학교": school,
            "EC 목표": ec,
            "개체수": count
        })

    st.table(pd.DataFrame(rows))

    all_env = pd.concat(env_data.values())
    c1, c2, c3, c4 = st.columns(4)

    c1.metric("총 개체수", total)
    c2.metric("평균 온도", f"{all_env['temperature'].mean():.1f} ℃")
    c3.metric("평균 습도", f"{all_env['humidity'].mean():.1f} %")
    c4.metric("최적 EC", "2.0 (하늘고) ⭐")

# ==================================================
# Tab 2: 환경 데이터
# ==================================================
with tab2:
    st.subheader("학교별 환경 평균 비교")

    avg = []
    for school, df in env_data.items():
        avg.append({
            "학교": school,
            "temperature": df["temperature"].mean(),
            "humidity": df["humidity"].mean(),
            "ph": df["ph"].mean(),
            "ec": df["ec"].mean(),
            "target_ec": EC_INFO[school]
        })

    avg_df = pd.DataFrame(avg)

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=("평균 온도", "평균 습도", "평균 pH", "목표 EC vs 실측 EC")
    )

    fig.add_bar(x=avg_df["학교"], y=avg_df["temperature"], row=1, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["humidity"], row=1, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ph"], row=2, col=1)
    fig.add_bar(x=avg_df["학교"], y=avg_df["ec"], name="실측 EC", row=2, col=2)
    fig.add_bar(x=avg_df["학교"], y=avg_df["target_ec"], name="목표 EC", row=2, col=2)

    fig.update_layout(height=700, font=PLOTLY_FONT)
    st.plotly_chart(fig, use_container_width=True)

    if selected_school != "전체":
        df = env_data[selected_school]

        fig_ts = make_subplots(rows=3, cols=1, shared_xaxes=True)
        fig_ts.add_scatter(x=df["time"], y=df["temperature"], row=1, col=1, name="온도")
        fig_ts.add_scatter(x=df["time"], y=df["humidity"], row=2, col=1, name="습도")
        fig_ts.add_scatter(x=df["time"], y=df["ec"], row=3, col=1, name="EC")

        fig_ts.add_hline(y=EC_INFO[selected_school], row=3, col=1, line_dash="dash")
        fig_ts.update_layout(height=700, font=PLOTLY_FONT)
        st.plotly_chart(fig_ts, use_container_width=True)

    with st.expander("환경 데이터 원본"):
        env_all = pd.concat(env_data.values())
        st.dataframe(env_all)

        buffer = io.BytesIO()
        env_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            label="환경데이터 XLSX 다운로드",
            data=buffer.getvalue(),
            file_name="환경데이터_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# ==================================================
# Tab 3: 생육 결과
# ==================================================
with tab3:
    growth_all = pd.concat(growth_data.values())
    growth_all["EC"] = growth_all["school"].map(EC_INFO)

    avg_weight = growth_all.groupby("EC")["생중량(g)"].mean()
    best_ec = avg_weight.idxmax()

    st.metric("🥇 최적 EC (평균 생중량)", f"{best_ec}")

    fig_bar = px.bar(
        avg_weight.reset_index(),
        x="EC",
        y="생중량(g)",
        title="EC별 평균 생중량"
    )
    fig_bar.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_bar, use_container_width=True)

    fig_box = px.box(
        growth_all,
        x="school",
        y="생중량(g)",
        color="school"
    )
    fig_box.update_layout(font=PLOTLY_FONT)
    st.plotly_chart(fig_box, use_container_width=True)

    with st.expander("생육 데이터 원본"):
        st.dataframe(growth_all)

        buffer = io.BytesIO()
        growth_all.to_excel(buffer, index=False, engine="openpyxl")
        buffer.seek(0)

        st.download_button(
            label="생육결과 XLSX 다운로드",
            data=buffer.getvalue(),
            file_name="생육결과_전체.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
