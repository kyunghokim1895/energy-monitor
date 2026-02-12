import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re
import html

st.set_page_config(page_title="에너지 모니터링", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 에너지/데이터센터 모니터링")

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        df.index = range(1, len(df) + 1)
        
        # 텍스트 정리 함수
        def clean_text(text):
            if not text: return text
            text = re.sub(r'<[^>]*>', '', text)
            return html.unescape(text)

        df['title'] = df['title'].apply(clean_text)

        # ---------------------------------------------------------
        # 🗺️ [지도 시각화 기능 추가]
        # 위도(lat), 경도(lon) 데이터가 있는 프로젝트만 골라냅니다.
        map_data = df.dropna(subset=['lat', 'lon'])

        if not map_data.empty:
            st.subheader(f"🗺️ 글로벌 프로젝트 지도 ({len(map_data)}개 위치)")
            # 스트림릿 내장 지도 기능 (lat, lon 컬럼을 자동으로 인식함)
            st.map(map_data, zoom=1)
        # ---------------------------------------------------------

        st.divider() # 구분선

        st.metric("총 수집 프로젝트", f"{len(df)}건")

        # 리스트/표 보기 모드
        st.sidebar.header("📱 보기 설정")
        view_mode = st.sidebar.radio("방식 선택", ["표로 보기 (PC)", "리스트 (모바일)"])

        if view_mode == "표로 보기 (PC)":
            st.dataframe(
                df.drop(columns=['id']), 
                use_container_width=True,
                height='content', 
                column_config={
                    "url": st.column_config.LinkColumn("기사", display_text="🔗"),
                    "title": st.column_config.Column("뉴스 제목", width="large"),
                    "created_at": "수집일시",
                    "lat": None, # 표에서는 위도/경도 숫자를 숨김 (지저분하니까)
                    "lon": None
                }
            )
        else:
            # 모바일 리스트 뷰
            for index, row in df.iterrows():
                with st.container():
                    st.markdown(f"### [{row['title']}]({row['url']})")
                    c1, c2 = st.columns(2)
                    c1.caption("📍 위치")
                    c1.write(row['location'] if row['location'] else "-")
                    c2.caption("⚡ 용량")
                    c2.write(f"{row['power_capacity_mw']} MW" if row['power_capacity_mw'] else "-")
                    st.divider()

    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류: {e}")