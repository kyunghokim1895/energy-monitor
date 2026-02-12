import os
import requests
import feedparser
from bs4 import BeautifulSoup
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
import urllib.parse
import json

load_dotenv()

# 설정 로드
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
NAVER_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET")

# 1. 수집 대상 설정
KEYWORDS = [
    "데이터센터 신축 용량",
    "데이터센터 특화단지",
    "데이터센터 SMR 원전",
    "데이터센터 액침냉각",
    "데이터센터 수주"
]

RSS_FEEDS = [
    {"name": "전자신문(IT)", "url": "https://www.etnews.com/etc/etnews_rss.html?igubun=0001"},
    {"name": "DCD(Global)", "url": "https://www.datacenterdynamics.com/en/rss/"} # 외국 기사 추가
]

def scrape_article(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=7)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 매체별 본문 태그 대응 (네이버, DCD 등)
        article = soup.select_one("#newsct_article") or soup.select_one(".article-body") or soup.select_one("article")
        return article.get_text(strip=True)[:2500] if article else ""
    except: return ""

def analyze_ai(text, lang="ko"):
    # 외국 기사일 경우 한글로 번역하여 추출하도록 프롬프트 수정
    prompt = f"너는 글로벌 에너지 분석가야. 다음 텍스트에서 정보를 추출해 JSON으로 응답해. 모든 값은 한국어로 번역해서 작성해. 필드: project_name, location, power_capacity_mw, energy_tech, pue_target, companies. 없으면 null."
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
        body = scrape_article(link)
        if len(body) > 300:
            analysis = analyze_ai(body)
            if analysis:
                for k in analysis:
                    if isinstance(analysis[k], list): analysis[k] = ", ".join(map(str, analysis[k]))
                analysis.update({"title": title, "url": link})
                supabase.table("projects").insert(analysis).execute()
                print(f"✅ 저장: {title[:30]}...")

def main():
    print("🚀 [1/2] 네이버 뉴스 검색 수집 시작 (Keyword-based)...")
    for kw in KEYWORDS:
        query = urllib.parse.quote(kw)
        url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=date"
        headers = {"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET}
        items = requests.get(url, headers=headers).json().get('items', [])
        for item in items:
            process_and_save(item['title'].replace('<b>','').replace('</b>',''), item['link'])

    print("\n🚀 [2/2] RSS 피드 수집 시작 (Source-based)...")
    for feed in RSS_FEEDS:
        print(f"📡 {feed['name']} 읽는 중...")
        parsed = feedparser.parse(feed['url'])
        for entry in parsed.entries[:10]: # 각 매체당 최신 10개
            process_and_save(entry.title, entry.link)

if __name__ == "__main__":
    main()