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
        df = pd.DataFrame(response.data)
        
        # 날짜 및 데이터 정리
        df['created_at_dt'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
        df['display_date'] = df['created_at_dt'].dt.strftime('%Y-%m-%d')
        
        # 필터 설정
        st.sidebar.header("🔍 필터 설정")
        period = st.sidebar.radio("조회 기간", ["최근 1개월", "최근 3개월", "전체 보기"], index=0)
        now = datetime.now()
        if period == "최근 1개월":
            limit_date = now - timedelta(days=30)
            df = df[df['created_at_dt'] >= limit_date]
        elif period == "최근 3개월":
            limit_date = now - timedelta(days=90)
            df = df[df['created_at_dt'] >= limit_date]
            
        # 순서 컬럼 생성 및 정리
        df = df.reset_index(drop=True)
        df['No.'] = df.index + 1
        
        def clean_text(text):
            if not text: return text
            text = re.sub(r'<[^>]*>', '', text)
            return html.unescape(text)
        df['title'] = df['title'].apply(clean_text)

        # ---------------------------------------------------------
        # 🗺️ 지도 시각화 (말풍선 배경색을 밝게 변경)
        # ---------------------------------------------------------
        map_data = df.dropna(subset=['lat', 'lon'])
        if not map_data.empty:
            st.subheader(f"🗺️ 글로벌 프로젝트 지도 ({len(map_data)}건)")
            st.caption("🔴 500MW 이상 | 🟠 100MW 이상 | 🟢 100MW 미만/미상")
            
            def parse_mw(val):
                nums = re.findall(r'\d+', str(val))
                return float(nums[0]) if nums else 0
            map_data['mw_num'] = map_data['power_capacity_mw'].apply(parse_mw)
            map_data['color'] = map_data['mw_num'].apply(lambda x: [200, 30, 30, 200] if x >= 500 else ([255, 140, 0, 200] if x >= 100 else [0, 150, 0, 200]))

            view_state = pdk.ViewState(latitude=map_data['lat'].mean(), longitude=map_data['lon'].mean(), zoom=1)
            layer = pdk.Layer("ScatterplotLayer", data=map_data, get_position='[lon, lat]', get_fill_color='color', get_radius=200000, pickable=True, auto_highlight=True)

            st.pydeck_chart(pdk.Deck(
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": """
                    <div style="font-family: sans-serif; padding: 10px;">
                        <b style="font-size: 14px;">{project_name}</b><br/>
                        <hr style="margin: 5px 0; border: 0.5px solid #ccc;">
                        📍 <b>위치:</b> {location}<br/>
                        ⚡ <b>용량:</b> {power_capacity_mw} MW
                    </div>
                    """,
                    "style": {
                        "backgroundColor": "#FFFFFF",  # 밝은 흰색 배경으로 변경
                        "color": "#000000",           # 글자색은 검은색
                        "border": "1px solid #777",
                        "zIndex": "10000"
                    }
                }
            ))

        st.divider()
        st.metric("조회된 프로젝트", f"{len(df)}건 ({period})")

        view_mode = st.sidebar.radio("목록 보기 방식", ["표 (PC)", "리스트 (모바일)"])

        if view_mode == "표 (PC)":
            # 불필요한 인덱스 숨기기 및 표 출력
            st.dataframe(
                df[['No.', 'title', 'url', 'project_name', 'location', 'power_capacity_mw', 'energy_tech', 'display_date']],
                use_container_width=True,
                height='content',
                hide_index=True,
                column_config={
                    "No.": st.column_config.Column("No.", width="small"),
                    "url": st.column_config.LinkColumn("기사", display_text="🔗 이동"),
                    "title": st.column_config.Column("뉴스 제목", width="large"),
                    "display_date": "수집일"
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
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")