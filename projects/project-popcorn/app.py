"""
Project Popcorn - Streamlit 메인 애플리케이션

입법 리스크 레이더 MVP
"""
import streamlit as st

st.set_page_config(
    page_title="Project Popcorn",
    page_icon="🍿",
    layout="wide"
)

st.title("🍿 Project Popcorn")
st.subheader("입법 리스크 레이더 (Legislative Risk Radar)")

st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("설정")
    ministry = st.selectbox(
        "모니터링 부처",
        ["산업통상자원부", "과학기술정보통신부", "환경부", "보건복지부"]
    )
    similarity_threshold = st.slider(
        "유사도 임계값",
        min_value=0.5,
        max_value=1.0,
        value=0.82,
        step=0.01
    )

# Main content
col1, col2 = st.columns(2)

with col1:
    st.header("📡 리스크 감지")
    st.info("신규 법안 스캔 대기 중...")
    # TODO: radar.scan_new_bills() 연동

with col2:
    st.header("🧠 분석 결과")
    st.info("감지된 리스크가 없습니다.")
    # TODO: 리스크 분석 결과 표시

st.markdown("---")
st.caption("Built with Upstage Solar & Qdrant | 15만원/월 예산 내 운영")
