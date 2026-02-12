import streamlit as st
import sqlite3
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="에너지 및 데이터센터 모니터링", layout="wide")

st.title("⚡ 실시간 에너지/데이터센터 모니터링 대시보드")

# 1. 데이터베이스에서 데이터 불러오기
def load_data():
    conn = sqlite3.connect("energy_data.db")
    query = "SELECT * FROM projects ORDER BY created_at DESC"
    df = pd.read_sql(query, conn)
    conn.close()
    return df

# 2. 화면 구성
try:
    df = load_data()

    if not df.empty:
        # 상단 요약 정보
        col1, col2 = st.columns(2)
        col1.metric("총 수집 프로젝트", f"{len(df)}건")
        col2.metric("최근 업데이트", df['created_at'].iloc[0][:19])

        st.divider()

        st.subheader("📋 수집된 프로젝트 리스트")
        # 출력할 칼럼 선택 및 이름 변경
        display_df = df[['created_at', 'project_name', 'location', 'power_capacity_mw', 'energy_tech', 'pue_target', 'companies', 'url']]
        
        # 표 출력
        st.dataframe(display_df, use_container_width=True)

    else:
        st.info("아직 수집된 데이터가 없습니다. main.py를 실행해 데이터를 먼저 수집해 주세요.")

except Exception as e:
    st.error(f"데이터 로드 중 오류 발생: {e}")

# 사이드바에 새로고침 버튼
if st.sidebar.button("데이터 새로고침"):
    st.rerun()