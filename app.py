import streamlit as st
import sqlite3
import pandas as pd
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import urllib.parse
import os

# 페이지 설정
st.set_page_config(page_title="에너지/데이터센터 모니터링", layout="wide")

# 1. API 키 설정 (Streamlit Secrets 사용)
# 로컬에서는 .env를 쓰지만, 서버에서는 st.secrets를 사용하도록 설정합니다.
try:
    NAVER_ID = st.secrets["NAVER_CLIENT_ID"]
    NAVER_SECRET = st.secrets["NAVER_CLIENT_SECRET"]
    OPENAI_KEY = st.secrets["OPENAI_API_KEY"]
except:
    # 로컬 테스트용 (Secrets가 없을 때 .env 로드)
    from dotenv import load_dotenv
    load_dotenv()
    NAVER_ID = os.getenv("NAVER_CLIENT_ID")
    NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET")
    OPENAI_KEY = os.getenv("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_KEY)

# 2. 데이터베이스 및 테이블 초기화 함수
def init_db():
    conn = sqlite3.connect("energy_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT, url TEXT UNIQUE, project_name TEXT,
            location TEXT, power_capacity_mw TEXT,
            energy_tech TEXT, pue_target TEXT, companies TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

# --- 수집 로직 (기존 main.py 내용 합침) ---
def scrape_article(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        article = soup.select_one("#newsct_article") or soup.select_one("#articleBodyContents") or soup.select_one("article")
        return article.get_text(strip=True)[:2000] if article else ""
    except: return ""

def analyze_ai(text):
    prompt = "에너지 분석가로서 project_name, location, power_capacity_mw, energy_tech, pue_target, companies 정보를 JSON으로 추출해. 없으면 null."
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
        response_format={ "type": "json_object" }
    )
    import json
    return json.loads(response.choices[0].message.content)

# 3. 메인 화면
st.title("⚡ 실시간 에너지/데이터센터 모니터링")

# 사이드바 - 데이터 수집 기능
st.sidebar.header("🕹️ 컨트롤 패널")
if st.sidebar.button("🔍 최신 데이터 수집 시작"):
    with st.spinner("뉴스를 분석 중입니다... 잠시만 기다려주세요."):
        conn = init_db()
        cursor = conn.cursor()
        
        # 뉴스 검색
        query = urllib.parse.quote("데이터센터 신축 용량")
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=date"
        headers = {"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET}
        items = requests.get(url, headers=headers).json().get('items', [])
        
        new_count = 0
        for item in items:
            link = item['link']
            cursor.execute("SELECT id FROM projects WHERE url = ?", (link,))
            if not cursor.fetchone():
                body = scrape_article(link)
                if len(body) > 200:
                    analysis = analyze_ai(body)
                    # 리스트를 문자열로 변환
                    for k in analysis:
                        if isinstance(analysis[k], list): analysis[k] = ", ".join(map(str, analysis[k]))
                    
                    cursor.execute("""
                        INSERT INTO projects (title, url, project_name, location, power_capacity_mw, energy_tech, pue_target, companies)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (item['title'], link, analysis.get('project_name'), analysis.get('location'),
                          analysis.get('power_capacity_mw'), analysis.get('energy_tech'),
                          analysis.get('pue_target'), analysis.get('companies')))
                    new_count += 1
        conn.commit()
        conn.close()
        st.sidebar.success(f"{new_count}개의 새로운 프로젝트를 찾았습니다!")
        st.rerun()

# 4. 데이터 표시 부분
conn = init_db() # 테이블이 없으면 생성
df = pd.read_sql("SELECT * FROM projects ORDER BY created_at DESC", conn)
conn.close()

if not df.empty:
    st.metric("총 수집 프로젝트", f"{len(df)}건")
    st.dataframe(df.drop(columns=['id']), use_container_width=True)
else:
    st.warning("현재 저장된 데이터가 없습니다. 왼쪽의 '최신 데이터 수집 시작' 버튼을 눌러주세요!")