import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re

st.set_page_config(page_title="에너지 모니터링", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 에너지/데이터센터 모니터링")

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        
        # 4번 해결: 인덱스를 1번부터 시작하도록 설정
        df.index = range(1, len(df) + 1)
        
        # 제목의 <b> 태그 등 HTML 태그 제거 (정규표현식 사용)
        df['title'] = df['title'].apply(lambda x: re.sub(r'<[^>]*>', '', x) if x else x)

        st.metric("총 수집 프로젝트", f"{len(df)}건")

        # 3번 해결: height를 None으로 설정하거나 큰 값을 주어 스크롤 없이 다 보이게 함
        # (기본적으로 st.dataframe은 높이가 고정되므로 height 파라미터를 조정합니다)
        st.dataframe(
            df.drop(columns=['id']), 
            use_container_width=True,
            height=2000, # 충분히 크게 설정하여 모든 기사가 한 번에 보이게 함
            column_config={
                "url": st.column_config.LinkColumn("기사", display_text="🔗"),
                "title": st.column_config.Column("뉴스 제목", width="large"),
                "created_at": "수집일시"
            }
        )
    else:
        st.info("데이터가 없습니다.")
except Exception as e:
    st.error(f"오류: {e}")