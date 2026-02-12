import streamlit as st
from supabase import create_client, Client
import pandas as pd

st.set_page_config(page_title="에너지 모니터링 클라우드", layout="wide")

# Supabase 연결
url = st.secrets["SUPABASE_URL"]
key = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(url, key)

st.title("⚡ 실시간 에너지/데이터센터 모니터링 (Cloud)")

try:
    response = supabase.table("projects").select("*").order("created_at", desc=True).execute()
    if response.data:
        df = pd.DataFrame(response.data)
        st.metric("총 수집 프로젝트", f"{len(df)}건")
        st.dataframe(df.drop(columns=['id']), use_container_width=True)
    else:
        st.info("데이터베이스가 비어 있습니다. 자동 수집을 기다리거나 수동 실행하세요.")
except Exception as e:
    st.error(f"데이터 로드 오류: {e}")