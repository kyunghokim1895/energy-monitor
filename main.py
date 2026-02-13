import os
import requests
import feedparser
from bs4 import BeautifulSoup
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
import urllib.parse
import json
import re
import datetime

load_dotenv()

# 환경 변수 로드 (로컬에서는 .env, 서버에서는 Secrets에서 로드)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
NAVER_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 1. 수집 대상 설정 (키워드 다양화 및 RSS 추가)
KEYWORDS = [
    "데이터센터 신축 용량", "데이터센터 특화단지", "데이터센터 SMR", 
    "데이터센터 액침냉각", "데이터센터 수주"
]
RSS_FEEDS = [
    {"name": "DCD(Global)", "url": "https://www.datacenterdynamics.com/en/rss/"},
    {"name": "DCK(Global)", "url": "https://www.datacenterknowledge.com/rss.xml"},
    {"name": "전자신문(KR)", "url": "https://www.etnews.com/etc/etnews_rss.html?igubun=0001"}
]

def scrape_article(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 본문 추출 로직 (다양한 패턴 시도)
        article = soup.select_one("#newsct_article") or soup.select_one(".article-body") or soup.select_one(".content-area") or soup.select_one("article")
        
        content = article.get_text(strip=True) if article else ""
        
        # 2차 안전장치: P 태그 긁어오기
        if len(content) < 500:
            p_tags = soup.find_all('p')
            content = " ".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 30])

        return content[:3500]
    except Exception as e:
        return ""

# main.py의 analyze_ai 함수 내부 프롬프트만 수정
def analyze_ai(text):
    # 좌표 추출을 더 강력하게 요청하도록 프롬프트를 수정합니다.
    prompt = """
    Analyze the text as an energy analyst. Extract info in JSON format.
    Keep original language for text fields.
    Fields: 
    - project_name
    - location (City, State/Country)
    - lat (Approximate latitude of the location, float) <-- 좌표 추출에 집중
    - lon (Approximate longitude of the location, float) <-- 좌표 추출에 집중
    - power_capacity_mw
    - energy_tech
    - pue_target
    - companies
    
    If location is not a clear geographic place (like Moon), set lat/lon to null.
    If info is missing, use null.
    """
    try:
        # ... (나머지 코드는 동일)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except: return None

def process_and_save(title, link):
    # 중복 체크 (Supabase)
    check = supabase.table("projects").select("id").eq("url", link).execute()
    if not check.data:
        print(f"🔍 분석 시도: {title[:30]}...")
        body = scrape_article(link)
        
        if len(body) > 100:
            analysis = analyze_ai(body)
            if analysis:
                # 리스트 -> 문자열 변환
                for k in analysis:
                    if isinstance(analysis[k], list): analysis[k] = ", ".join(map(str, analysis[k]))
                
                # 데이터 삽입
                analysis.update({"title": title, "url": link})
                supabase.table("projects").insert(analysis).execute()
                print(f"✅ 저장 완료!")
        else:
            print(f"⚠️ 스킵: 본문 추출 실패 또는 짧음")

def main():
    print("🚀 [1/2] 네이버 뉴스 검색 수집 시작...")
    for kw in KEYWORDS:
        query = urllib.parse.quote(kw)
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=date" # 5개씩으로 줄임
        headers = {"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET}
        try:
            items = requests.get(url, headers=headers).json().get('items', [])
            for item in items:
                process_and_save(item['title'].replace('<b>','').replace('</b>',''), item['link'])
        except: pass

    print("\n🚀 [2/2] 글로벌 RSS 피드 수집 시작...")
    for feed in RSS_FEEDS:
        print(f"📡 {feed['name']} 접속 중...")
        try:
            parsed = feedparser.parse(feed['url'])
            for entry in parsed.entries[:5]: # 각 매체당 최신 5개
                process_and_save(entry.title, entry.link)
        except Exception as e:
            print(f"RSS 에러: {e}")

if __name__ == "__main__":
    # 로컬 테스트 시 데이터베이스에 저장하는 대신 콘솔에 출력
    if 'RUNNER_ENVIRONMENT' not in os.environ:
        print("\n--- 로컬 테스트 모드: DB 대신 콘솔에 출력됩니다. ---")
        # (로컬 테스트용으로 DB 저장 대신 콘솔 출력 코드를 넣을 수도 있습니다.)
        print("로컬에서는 DB 대신 웹 대시보드 확인용으로만 사용하세요.")
    else:
        main()