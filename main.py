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

load_dotenv()

# 환경 변수 로드
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
NAVER_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 수집 키워드 및 RSS 목록
KEYWORDS = ["데이터센터 신축", "데이터센터 전력", "데이터센터 수주"]
RSS_FEEDS = [
    # 글로벌 리딩 매체 (DCD)
    {"name": "DCD", "url": "https://www.datacenterdynamics.com/en/rss/"},
    # 데이터센터 지식 (Global)
    {"name": "DCK", "url": "https://www.datacenterknowledge.com/rss.xml"},
    # 국내 전문지
    {"name": "전자신문", "url": "https://www.etnews.com/etc/etnews_rss.html?igubun=0001"}
]

def scrape_article(url):
    try:
        # 봇 차단 방지를 위한 헤더 설정
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        content = ""
        
        # 1차 시도: 주요 뉴스 사이트들의 본문 태그 패턴 탐색
        selectors = [
            "#newsct_article", ".article-body", ".content-body", 
            "article", ".post-content", ".story-body", "#article-view-content-div"
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                content = element.get_text(strip=True)
                break
        
        # 2차 시도 (안전장치): 만약 위에서 못 찾았으면, 그냥 모든 <p> 태그를 긁어옴
        if len(content) < 50:
            p_tags = soup.find_all('p')
            # 너무 짧은 문장(메뉴 등)은 제외하고 본문 같은 것만 합침
            content = " ".join([p.get_text(strip=True) for p in p_tags if len(p.get_text(strip=True)) > 30])

        return content[:3500] # 너무 길면 자름
    except Exception as e:
        print(f"❌ 스크래핑 에러: {e}")
        return ""

def analyze_ai(text):
    # 영문은 영문 그대로, 한글은 한글 그대로 추출 요청
    prompt = """
    Analyze the text as an energy analyst. Extract info in JSON format.
    Keep original language (English->English, Korean->Korean).
    Fields: project_name, location, power_capacity_mw, energy_tech, pue_target, companies.
    If info is missing, use null.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except: return None

def process_and_save(title, link):
    # 중복 체크
    check = supabase.table("projects").select("id").eq("url", link).execute()
    if not check.data:
        print(f"🔍 분석 시도: {title[:30]}...")
        body = scrape_article(link)
        
        # 본문이 100자 이상일 때만 분석 (너무 짧으면 스킵)
        if len(body) > 100:
            analysis = analyze_ai(body)
            if analysis:
                # 리스트 -> 문자열 변환
                for k in analysis:
                    if isinstance(analysis[k], list): analysis[k] = ", ".join(map(str, analysis[k]))
                
                analysis.update({"title": title, "url": link})
                supabase.table("projects").insert(analysis).execute()
                print(f"✅ 저장 완료!")
        else:
            print(f"⚠️ 본문 추출 실패 (내용이 너무 짧음)")

def main():
    print("🚀 [1/2] 네이버 뉴스 검색...")
    for kw in KEYWORDS:
        query = urllib.parse.quote(kw)
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=5&sort=date"
        headers = {"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET}
        try:
            items = requests.get(url, headers=headers).json().get('items', [])
            for item in items:
                process_and_save(item['title'].replace('<b>','').replace('</b>',''), item['link'])
        except: pass

    print("\n🚀 [2/2] 글로벌 RSS 피드 수집...")
    for feed in RSS_FEEDS:
        print(f"📡 {feed['name']} 접속 중...")
        try:
            parsed = feedparser.parse(feed['url'])
            # 최신 글 5개씩만 확인
            for entry in parsed.entries[:5]:
                process_and_save(entry.title, entry.link)
        except Exception as e:
            print(f"RSS 에러: {e}")

if __name__ == "__main__":
    main()