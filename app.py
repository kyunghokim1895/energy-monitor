import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re
import html
import pydeck as pdk  # 지도를 그리기 위한 도구

st.set_page_config(page_title="에너지 모니터링", layout="wide")

# Supabase 연결
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 에너지/데이터센터 모니터링")

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        df.index = range(1, len(df) + 1)
        
        # 텍스트 정리
        def clean_text(text):
            if not text: return text
            text = re.sub(r'<[^>]*>', '', text)
            return html.unescape(text)

        df['title'] = df['title'].apply(clean_text)

        # ---------------------------------------------------------
        # 🗺️ [업그레이드된 지도 기능]
        # ---------------------------------------------------------
        map_data = df.dropna(subset=['lat', 'lon'])

        if not map_data.empty:
            st.subheader(f"🗺️ 글로벌 프로젝트 지도 ({len(map_data)}개)")
            
            # 지도 설정 (초기 위치 및 줌)
            view_state = pdk.ViewState(
                latitude=map_data['lat'].mean(),
                longitude=map_data['lon'].mean(),
                zoom=2,
                pitch=0,
            )

            # 레이어 설정 (빨간 점 표시 및 툴팁 데이터 연결)
            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_data,
                get_position='[lon, lat]',
                get_color='[255, 0, 0, 160]',  # 빨간색 (RGB + 투명도)
                get_radius=200000,             # 점 크기 (미터 단위, 200km 반경)
                pickable=True,                 # 마우스 선택 가능 여부 (필수!)
                auto_highlight=True,
            )

            # 지도 그리기 (툴팁 설정 포함)
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": "<b>프로젝트:</b> {project_name}<br/>"
                            "<b>위치:</b> {location}<br/>"
                            "<b>용량:</b> {power_capacity_mw} MW<br/>"
                            "<b>기술:</b> {energy_tech}",
                    "style": {
                        "backgroundColor": "steelblue",
                        "color": "white"
                    }
                }
            ))
        # ---------------------------------------------------------

        st.metric("총 수집 프로젝트", f"{len(df)}건")

        # 보기 설정
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
                    "lat": None, 
                    "lon": None
                }
            )
        else:
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