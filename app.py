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
        
        # 날짜 변환 및 정리
        df['created_at_dt'] = pd.to_datetime(df['created_at']).dt.tz_localize(None)
        df['display_date'] = df['created_at_dt'].dt.strftime('%Y-%m-%d')
        
        # 🧹 사이드바 필터
        st.sidebar.header("🔍 필터 설정")
        period = st.sidebar.radio("조회 기간", ["최근 1개월", "최근 3개월", "전체 보기"], index=0)
        now = datetime.now()
        if period == "최근 1개월":
            limit_date = now - timedelta(days=30)
            df = df[df['created_at_dt'] >= limit_date]
        elif period == "최근 3개월":
            limit_date = now - timedelta(days=90)
            df = df[df['created_at_dt'] >= limit_date]
            
        st.sidebar.divider()
        
        # 🎨 핀 색깔 구분 로직
        def parse_mw(value):
            try:
                nums = re.findall(r'\d+', str(value))
                return float(nums[0]) if nums else 0
            except:
                return 0

        df['mw_num'] = df['power_capacity_mw'].apply(parse_mw)

        def get_color(mw):
            if mw >= 500: return [200, 30, 30, 200]
            elif mw >= 100: return [255, 140, 0, 200]
            else: return [0, 150, 0, 200]

        df['color'] = df['mw_num'].apply(get_color)
        
        def clean_text(text):
            if not text: return text
            text = re.sub(r'<[^>]*>', '', text)
            return html.unescape(text)

        df['title'] = df['title'].apply(clean_text)
        
        # ---------------------------------------------------------
        # 🗺️ 지도 시각화 (툴팁 정보 강화 및 지도 표시)
        # ---------------------------------------------------------
        map_data = df.dropna(subset=['lat', 'lon'])

        if not map_data.empty:
            st.subheader(f"🗺️ 글로벌 프로젝트 지도 ({len(map_data)}건)")
            st.caption("🔴 500MW 이상 | 🟠 100MW 이상 | 🟢 100MW 미만/미상")

            view_state = pdk.ViewState(
                latitude=map_data['lat'].mean() if not map_data.empty else 0,
                longitude=map_data['lon'].mean() if not map_data.empty else 0,
                zoom=1, pitch=0,
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_data,
                get_position='[lon, lat]',
                get_fill_color='color',
                get_radius=200000,
                pickable=True,
                auto_highlight=True,
            )

            # 툴팁 정보를 강화하여 표시 (HTML 포맷 사용)
            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": "<b>프로젝트:</b> {project_name}<br/>"
                            "📍 위치: {location}<br/>"
                            "⚡ 용량: {power_capacity_mw} MW<br/>"
                            "🏢 기업: {companies}",
                    "style": {"backgroundColor": "#1E1E1E", "color": "white"}
                }
            ))
        else:
            st.info("지도에 표시할 좌표(lat/lon) 데이터가 없습니다.")

        st.divider()
        st.metric("조회된 프로젝트", f"{len(df)}건 ({period})")

        # --- 보기 방식 선택 ---
        view_mode = st.sidebar.radio("목록 보기 방식", ["리스트 (모바일)", "표 (PC)"])

        if view_mode == "표 (PC)":
            st.dataframe(
                df.drop(columns=['id', 'lat', 'lon', 'mw_num', 'created_at_dt', 'color']),
                use_container_width=True,
                height='content', 
                column_config={
                    "url": st.column_config.LinkColumn("기사", display_text="🔗 이동"),
                    "title": st.column_config.Column("뉴스 제목", width="large"),
                    "display_date": "수집일",
                    "power_capacity_mw": "용량(MW)",
                    # 2번 해결: 목차 번호 컬럼(index+1)의 정렬 설정
                    "목차": st.column_config.Column(
                        "순서", 
                        width="small", 
                        horizontal_alignment="center" # 가운데 정렬
                    ),
                }
            )
        else:
            # 리스트 뷰 (1번부터 시작하는 row.name 사용)
            for index, row in df.iterrows():
                with st.container():
                    st.markdown(f"### {row.name}. [{row['title']}]({row['url']})")
                    c1, c2, c3 = st.columns(3)
                    c1.caption("📍 위치")
                    c1.write(row['location'] if row['location'] else "-")
                    if row['mw_num'] >= 500:
                        c2.markdown(f"⚡ :red[**{row['power_capacity_mw']} MW**]")
                    else:
                        c2.write(f"⚡ {row['power_capacity_mw']} MW" if row['power_capacity_mw'] else "-")
                    c3.caption("📅 날짜")
                    c3.write(row['display_date'])
                    st.divider()

    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류 발생: {e}")