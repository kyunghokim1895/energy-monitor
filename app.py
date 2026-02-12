import streamlit as st
from supabase import create_client, Client
import pandas as pd

# 페이지 설정
st.set_page_config(page_title="에너지 모니터링 클라우드", layout="wide")

# Supabase 연결
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 실시간 에너지/데이터센터 모니터링")

try:
    # 데이터 가져오기
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        
        # 1. 요약 메트릭
        st.metric("총 수집 프로젝트", f"{len(df)}건")
        
        # 2. 표 설정 (LinkColumn 활용)
        # created_at 날짜 형식 예쁘게 변경 (선택 사항)
        df['created_at'] = pd.to_datetime(df['created_at']).dt.strftime('%Y-%m-%d %H:%M')

        st.subheader("📋 최신 프로젝트 목록")
        
        # ⭐ 스트림릿의 컬럼 설정 기능을 사용하여 URL을 클릭 가능한 링크로 만듭니다.
        st.dataframe(
            df.drop(columns=['id']), 
            use_container_width=True,
            column_config={
                "url": st.column_config.LinkColumn(
                    "기사 원문",
                    help="클릭하면 해당 뉴스 기사로 이동합니다",
                    display_text="🔗 보러가기" # 링크 주소 대신 '보러가기'라는 글자로 표시
                ),
                "title": st.column_config.Column(
                    "뉴스 제목",
                    width="large" # 제목 칸을 넓게 설정
                ),
                "project_name": "프로젝트명",
                "power_capacity_mw": "용량(MW)",
                "created_at": "수집 일시"
            }
        )
    else:
        st.info("데이터베이스가 비어 있습니다. 자동 수집을 기다리거나 수동 실행하세요.")

except Exception as e:
    st.error(f"데이터 로드 오류: {e}")