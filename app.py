import streamlit as st
from supabase import create_client, Client
import pandas as pd
import re
import html  # 특수문자 변환을 위해 추가

st.set_page_config(page_title="에너지 모니터링", layout="wide")

url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 에너지/데이터센터 모니터링")

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    
    if response.data:
        df = pd.DataFrame(response.data)
        
        # 4번 해결: 인덱스를 1번부터 시작
        df.index = range(1, len(df) + 1)
        
        # 3번 해결: HTML 태그 제거 및 &quot; 같은 특수문자 복원
        def clean_text(text):
            if not text: return text
            # 1. <b> 태그 등 제거
            text = re.sub(r'<[^>]*>', '', text)
            # 2. &quot; -> " 등 특수기호 변환
            text = html.unescape(text)
            return text

        df['title'] = df['title'].apply(clean_text)

        st.metric("총 수집 프로젝트", f"{len(df)}건")

        # 1번 해결: height=None으로 설정하면 데이터 개수에 딱 맞게 표가 끝납니다.
        st.dataframe(
            df.drop(columns=['id']), 
            use_container_width=True,
            height=None, 
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