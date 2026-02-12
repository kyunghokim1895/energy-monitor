import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re
import html
import pydeck as pdk
from datetime import datetime, timedelta

st.set_page_config(page_title="에너지 모니터링", layout="wide")

# Supabase 연결
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 에너지/데이터센터 모니터링")

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        all_df = pd.DataFrame(response.data)
        
        # 시간대 제거 및 날짜 정리
        all_df['created_at_dt'] = pd.to_datetime(all_df['created_at']).dt.tz_localize(None)
        all_df['display_date'] = all_df['created_at_dt'].dt.strftime('%Y-%m-%d')
        
        # 1. 사이드바 필터 설정
        st.sidebar.header("🔍 필터 설정")
        period = st.sidebar.radio("조회 기간", ["최근 1개월", "최근 3개월", "전체 보기"], index=0)
        
        now = datetime.now()
        df = all_df.copy() # 화면 표시용 데이터
        
        if period == "최근 1개월":
            df = df[df['created_at_dt'] >= (now - timedelta(days=30))]
        elif period == "최근 3개월":
            df = df[df['created_at_dt'] >= (now - timedelta(days=90))]

        # 데이터 정리 (No.를 텍스트로 변환하여 가운데 정렬 유도)
        df = df.reset_index(drop=True)
        df['No.'] = (df.index + 1).astype(str) # 숫자를 문자로 바꿔서 정렬 이슈 해결 시도
        
        def clean_text(text):
            if not text: return text
            text = re.sub(r'<[^>]*>', '', text)
            return html.unescape(text)
        df['title'] = df['title'].apply(clean_text)

        # ---------------------------------------------------------
        # 🗺️ 지도 시각화 (사라짐 방지를 위해 all_df 기준 또는 필터 체크)
        # ---------------------------------------------------------
        # 좌표가 있는 모든 데이터를 사용하거나, 필터링된 데이터 중 좌표 있는 것 선택
        map_data = df.dropna(subset=['lat', 'lon']).copy()

        if not map_data.empty:
            st.subheader(f"🗺️ 글로벌 프로젝트 지도 ({len(map_data)}건)")
            
            # MW 색상 로직
            def parse_mw(val):
                nums = re.findall(r'\d+', str(val))
                return float(nums[0]) if nums else 0
            map_data['mw_num'] = map_data['power_capacity_mw'].apply(parse_mw)
            map_data['color'] = map_data['mw_num'].apply(lambda x: [200, 30, 30, 230] if x >= 500 else ([255, 140, 0, 230] if x >= 100 else [0, 150, 0, 230]))

            view_state = pdk.ViewState(
                latitude=map_data['lat'].mean(), 
                longitude=map_data['lon'].mean(), 
                zoom=1
            )
            
            layer = pdk.Layer(
                "ScatterplotLayer", 
                data=map_data, 
                get_position='[lon, lat]', 
                get_fill_color='color', 
                get_radius=250000, # 점 크기 살짝 키움
                pickable=True, 
                auto_highlight=True
            )

            st.pydeck_chart(pdk.Deck(
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": """
                    <div style="font-family: sans-serif; padding: 10px; background-color: #A0C4FF; border-radius: 8px;">
                        <b style="font-size: 15px; color: #1E1E1E;">{project_name}</b><br/>
                        <hr style="margin: 5px 0; border: 0.5px solid #555;">
                        <span style="color: #2D3436;">📍 <b>위치:</b> {location}</span><br/>
                        <span style="color: #2D3436;">⚡ <b>용량:</b> {power_capacity_mw} MW</span>
                    </div>
                    """,
                    "style": {"backgroundColor": "transparent", "color": "transparent", "border": "none"}
                }
            ))
        else:
            st.info("현재 필터 범위 내에 지도에 표시할 좌표 데이터가 없습니다. '전체 보기'를 선택해 보세요.")

        st.divider()
        st.metric("조회된 프로젝트", f"{len(df)}건 ({period})")

        # --- 목록 보기 방식 ---
        view_mode = st.sidebar.radio("목록 보기 방식", ["표 (PC)", "리스트 (모바일)"])

        if view_mode == "표 (PC)":
            st.dataframe(
                df[['No.', 'title', 'url', 'project_name', 'location', 'power_capacity_mw', 'energy_tech', 'display_date']],
                use_container_width=True,
                height='content',
                hide_index=True,
                column_config={
                    "No.": st.column_config.Column("No.", width="small"),
                    "url": st.column_config.LinkColumn("기사", display_text="🔗 이동"),
                    "title": st.column_config.Column("뉴스 제목", width="large"),
                }
            )
        else:
            for index, row in df.iterrows():
                with st.container():
                    st.markdown(f"### {row['No.']}. [{row['title']}]({row['url']})")
                    c1, c2, c3 = st.columns(3)
                    c1.caption("📍 위치")
                    c1.write(row['location'] if row['location'] else "-")
                    c2.caption("⚡ 용량")
                    c2.write(f"{row['power_capacity_mw']} MW" if row['power_capacity_mw'] else "-")
                    c3.caption("📅 날짜")
                    c3.write(row['display_date'])
                    st.divider()
    else:
        st.warning("데이터베이스가 비어 있습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")