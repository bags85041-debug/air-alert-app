import math
from pathlib import Path

import matplotlib.pyplot as plt
import streamlit as st
from matplotlib import font_manager

from ai_helper import ask_ai
from air_api import get_sido, get_station

FONT_PATH = Path(__file__).parent / "fonts" / "NanumGothic-Regular.ttf"
font_manager.fontManager.addfont(str(FONT_PATH))
plt.rcParams["font.family"] = font_manager.FontProperties(fname=str(FONT_PATH)).get_name()
plt.rcParams["axes.unicode_minus"] = False

SIDO_LIST = [
    "서울", "부산", "대구", "인천", "광주", "대전", "울산", "세종",
    "경기", "강원", "충북", "충남", "전북", "전남", "경북", "경남", "제주",
]
GRADE_NAME = {"1": "좋음", "2": "보통", "3": "나쁨", "4": "매우나쁨"}


def to_num(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def grade_text(code):
    return GRADE_NAME.get(str(code), "정보 없음")


def fmt(value):
    return "-" if math.isnan(value) else f"{value:.0f}"


@st.cache_data(ttl=600)
def load_station_names(sido):
    items = get_sido(sido)
    return sorted({item["stationName"] for item in items})


@st.cache_data(ttl=600)
def load_station_records(station):
    items = get_station(station)
    records = [
        {
            "time": item["dataTime"],
            "pm10": to_num(item.get("pm10Value")),
            "pm25": to_num(item.get("pm25Value")),
            "pm10_grade": item.get("pm10Grade"),
            "pm25_grade": item.get("pm25Grade"),
        }
        for item in items
    ]
    records.sort(key=lambda r: r["time"])
    return [r for r in records if not (math.isnan(r["pm10"]) and math.isnan(r["pm25"]))]


st.set_page_config(page_title="미세먼지 알림", layout="wide")
st.title("미세먼지 알림 앱")

sido = st.selectbox("시·도 선택", SIDO_LIST)

try:
    station_names = load_station_names(sido)
except Exception as e:
    st.error(f"측정소 목록을 불러오지 못했습니다: {e}")
    st.stop()

station = st.selectbox("측정소 선택", station_names)

if st.button("조회", type="primary"):
    try:
        records = load_station_records(station)
    except Exception as e:
        st.error(f"측정값을 불러오지 못했습니다: {e}")
        st.stop()

    if not records:
        st.warning("해당 측정소의 측정값이 없습니다.")
        st.stop()

    latest = records[-1]
    st.caption(f"측정소: {station} · 최신 측정 시각: {latest['time']}")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("PM10 (㎍/㎥)", fmt(latest["pm10"]))
    c2.metric("PM10 등급", grade_text(latest["pm10_grade"]))
    c3.metric("PM2.5 (㎍/㎥)", fmt(latest["pm25"]))
    c4.metric("PM2.5 등급", grade_text(latest["pm25_grade"]))

    times = [r["time"][11:16] for r in records]
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(times, [r["pm10"] for r in records], marker="o", label="PM10")
    ax.plot(times, [r["pm25"] for r in records], marker="o", label="PM2.5")
    ax.set_title("오늘 미세먼지 추이")
    ax.set_ylabel("㎍/㎥")
    ax.legend()
    ax.tick_params(axis="x", rotation=45)
    fig.tight_layout()
    st.pyplot(fig)
    plt.close(fig)

    prompt = (
        f"{station} 측정소의 최신 미세먼지 정보입니다.\n"
        f"측정 시각: {latest['time']}\n"
        f"PM10: {fmt(latest['pm10'])} ㎍/㎥ (등급: {grade_text(latest['pm10_grade'])})\n"
        f"PM2.5: {fmt(latest['pm25'])} ㎍/㎥ (등급: {grade_text(latest['pm25_grade'])})\n"
        "일반인을 위해 외출, 마스크 착용, 실내 환경 관리 등 행동 요령을 "
        "3~4문장의 한국어로 짧게 안내해 주세요."
    )
    with st.spinner("AI 안내 문장을 만드는 중..."):
        try:
            advice = ask_ai(prompt)
        except Exception as e:
            advice = f"AI 안내를 가져오지 못했습니다: {e}"

    with st.container(border=True):
        st.subheader("AI 안내")
        st.markdown(advice)
