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
    # 3번 해결: 데이터 가져오기 (전체를 가져와서 파이썬에서 필터링)
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        
        # 날짜 변환
        df['created_at_dt'] = pd.to_datetime(df['created_at'])
        df['display_date'] = df['created_at_dt'].dt.strftime('%Y-%m-%d')
        
        # ---------------------------------------------------------
        # 🧹 [데이터 정리 규칙] 사이드바 필터
        # ---------------------------------------------------------
        st.sidebar.header("🔍 필터 설정")
        
        # 기간 필터
        period = st.sidebar.radio(
            "조회 기간", 
            ["최근 1개월", "최근 3개월", "전체 보기"], 
            index=0 # 기본값: 최근 1개월 (화면 깔끔하게 유지)
        )
        
        if period == "최근 1개월":
            limit_date = datetime.now() - timedelta(days=30)
            df = df[df['created_at_dt'] >= limit_date]
        elif period == "최근 3개월":
            limit_date = datetime.now() - timedelta(days=90)
            df = df[df['created_at_dt'] >= limit_date]
            
        st.sidebar.divider()
        
        # ---------------------------------------------------------
        # 🎨 [핀 색깔 구분 로직]
        # ---------------------------------------------------------
        def parse_mw(value):
            try:
                # "4500", "100 MW" 등에서 숫자만 추출
                nums = re.findall(r'\d+', str(value))
                return float(nums[0]) if nums else 0
            except:
                return 0

        # MW 숫자로 변환
        df['mw_num'] = df['power_capacity_mw'].apply(parse_mw)

        # 색상 지정 함수 (R, G, B, A)
        def get_color(mw):
            if mw >= 500:
                return [200, 30, 30, 200]   # 🔴 빨강 (초대형)
            elif mw >= 100:
                return [255, 140, 0, 200]   # 🟠 주황 (대형)
            else:
                return [0, 150, 0, 200]     # 🟢 초록 (일반/미상)

        df['color'] = df['mw_num'].apply(get_color)
        
        # 텍스트 정리
        def clean_text(text):
            if not text: return text
            text = re.sub(r'<[^>]*>', '', text)
            return html.unescape(text)

        df['title'] = df['title'].apply(clean_text)
        
        # 인덱스 재설정
        df.reset_index(drop=True, inplace=True)
        df.index = df.index + 1

        # ---------------------------------------------------------
        # 🗺️ 지도 시각화
        # ---------------------------------------------------------
        map_data = df.dropna(subset=['lat', 'lon'])

        if not map_data.empty:
            st.subheader(f"🗺️ 글로벌 프로젝트 지도 ({len(map_data)}건)")
            
            # 범례 설명
            st.caption("🔴 500MW 이상 (초대형) | 🟠 100MW 이상 (대형) | 🟢 100MW 미만/미상")

            view_state = pdk.ViewState(
                latitude=map_data['lat'].mean(),
                longitude=map_data['lon'].mean(),
                zoom=1,
                pitch=0,
            )

            layer = pdk.Layer(
                "ScatterplotLayer",
                data=map_data,
                get_position='[lon, lat]',
                get_fill_color='color',        # 위에서 만든 색상 적용
                get_radius=200000,
                pickable=True,
                auto_highlight=True,
            )

            st.pydeck_chart(pdk.Deck(
                map_style=None,
                initial_view_state=view_state,
                layers=[layer],
                tooltip={
                    "html": "<b>{project_name}</b><br/>"
                            "📍 {location}<br/>"
                            "⚡ {power_capacity_mw} MW<br/>"
                            "🏢 {companies}",
                    "style": {"backgroundColor": "#1E1E1E", "color": "white"}
                }
            ))

        # ---------------------------------------------------------
        # 📋 리스트 출력
        # ---------------------------------------------------------
        st.divider()
        st.metric("조회된 프로젝트", f"{len(df)}건 ({period})")

        view_mode = st.sidebar.radio("목록 보기 방식", ["리스트 (모바일)", "표 (PC)"])

        if view_mode == "표 (PC)":
            st.dataframe(
                df,
                use_container_width=True,
                height='content', 
                column_config={
                    "url": st.column_config.LinkColumn("링크", display_text="🔗 이동"),
                    "title": st.column_config.Column("뉴스 제목", width="large"),
                    "display_date": "수집일",
                    "power_capacity_mw": "용량(MW)",
                    "lat": None, "lon": None, "mw_num": None, "color": None, "created_at": None, "created_at_dt": None # 숨길 컬럼
                }
            )
        else:
            for index, row in df.iterrows():
                with st.container():
                    st.markdown(f"### [{row['title']}]({row['url']})")
                    c1, c2, c3 = st.columns(3)
                    c1.caption("📍 위치")
                    c1.write(row['location'] if row['location'] else "-")
                    
                    c2.caption("⚡ 용량")
                    # 용량에 따라 색상 강조
                    if row['mw_num'] >= 500:
                        c2.markdown(f":red[**{row['power_capacity_mw']} MW**]")
                    else:
                        c2.write(f"{row['power_capacity_mw']} MW" if row['power_capacity_mw'] else "-")
                        
                    c3.caption("📅 날짜")
                    c3.write(row['display_date'])
                    st.divider()

    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"오류: {e}")