import os
import json
import sqlite3
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from openai import OpenAI
import urllib.parse

# 1. 환경 변수 로드
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 2. 데이터베이스 초기화
def init_db():
    conn = sqlite3.connect("energy_data.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            url TEXT UNIQUE,
            project_name TEXT,
            location TEXT,
            power_capacity_mw TEXT,
            energy_tech TEXT,
            pue_target TEXT,
            companies TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn

# 3. 뉴스 검색
def search_news(keyword, display=5):
    encText = urllib.parse.quote(keyword)
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&display={display}&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_CLIENT_ID, "X-Naver-Client-Secret": NAVER_CLIENT_SECRET}
    response = requests.get(url, headers=headers)
    return response.json().get('items', []) if response.status_code == 200 else []

# 4. 본문 스크래핑
def scrape_article_body(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(res.text, 'html.parser')
        article = soup.select_one("#newsct_article") or soup.select_one("#articleBodyContents") or soup.select_one("article")
        return article.get_text(strip=True)[:2000] if article else ""
    except:
        return ""

# 5. AI 분석
def analyze_with_ai(text):
    print("🤖 AI 분석 중...")
    system_prompt = "너는 에너지 전문 분석가야. 기사 내용을 분석해 project_name, location, power_capacity_mw, energy_tech, pue_target, companies 정보를 JSON으로 출력해. 정보가 없으면 null로 표시해."
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": text}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except:
        return None

# 6. 메인 로직 (수정됨)
def main():
    conn = init_db()
    cursor = conn.cursor()
    
    keyword = "데이터센터 신축 용량"
    print(f"🚀 실시간 모니터링 시작: {keyword}")
    
    news_items = search_news(keyword, display=10)
    
    new_count = 0
    for item in news_items:
        title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
        link = item['link']
        
        cursor.execute("SELECT id FROM projects WHERE url = ?", (link,))
        if cursor.fetchone():
            continue
        
        print(f"\n✨ 새 기사 발견: {title}")
        body_text = scrape_article_body(link)
        
        if len(body_text) > 200:
            analysis = analyze_with_ai(body_text)
            if analysis:
                # ⭐ [수정 핵심] 리스트 형태의 데이터를 문자열로 변환하는 안전장치
                for key in analysis:
                    if isinstance(analysis[key], list):
                        analysis[key] = ", ".join(map(str, analysis[key]))
                
                try:
                    cursor.execute("""
                        INSERT INTO projects (title, url, project_name, location, power_capacity_mw, energy_tech, pue_target, companies)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (title, link, analysis.get('project_name'), analysis.get('location'), 
                          analysis.get('power_capacity_mw'), analysis.get('energy_tech'), 
                          analysis.get('pue_target'), analysis.get('companies')))
                    conn.commit()
                    print(f"✅ 저장 완료: {analysis.get('project_name')}")
                    new_count += 1
                except Exception as db_err:
                    print(f"❌ DB 저장 오류: {db_err}")
        
    print(f"\n🏁 분석 종료. 새로운 프로젝트 {new_count}건을 발견하여 DB에 저장했습니다.")
    conn.close()

if __name__ == "__main__":
    main()