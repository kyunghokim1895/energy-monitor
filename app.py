import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="에너지 모니터링", layout="wide")

# Supabase 연결
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 에너지/데이터센터 모니터링")

# 사이드바 설정
st.sidebar.header("📱 보기 설정")
view_mode = st.sidebar.radio("데이터 출력 방식", ["표로 보기 (PC 권장)", "리스트로 보기 (모바일 권장)"])

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%m-%d %H:%M')
        
        st.metric("총 수집 프로젝트", f"{len(df)}건")

        # --- 방식 1: 표로 보기 (가로 스크롤 포함) ---
        if view_mode == "표로 보기 (PC 권장)":
            st.dataframe(
                df.drop(columns=['id']), 
                use_container_width=True,
                column_config={
                    "url": st.column_config.LinkColumn("기사", display_text="🔗"),
                    "title": st.column_config.Column("뉴스 제목", width="large"),
                    "project_name": "프로젝트명",
                    "power_capacity_mw": "MW",
                    "created_at": "일시"
                }
            )

        # --- 방식 2: 리스트로 보기 (모바일 최적화 카드형) ---
        else:
            for index, row in df.iterrows():
                with st.container():
                    # 제목과 링크를 하나로 묶음
                    st.markdown(f"### [{row['title']}]({row['url']})")
                    
                    # 주요 정보를 한 줄씩 표현
                    c1, c2, c3 = st.columns(3)
                    c1.caption("📍 위치")
                    c1.write(row['location'] if row['location'] else "-")
                    
                    c2.caption("⚡ 용량")
                    c2.write(row['power_capacity_mw'] if row['power_capacity_mw'] else "-")
                    
                    c3.caption("🏢 기업")
                    c3.write(row['companies'] if row['companies'] else "-")
                    
                    with st.expander("🔍 상세 정보 보기"):
                        st.write(f"**에너지 기술:** {row['energy_tech']}")
                        st.write(f"**PUE 목표:** {row['pue_target']}")
                        st.write(f"**수집 시각:** {row['created_at']}")
                    st.divider()

    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")