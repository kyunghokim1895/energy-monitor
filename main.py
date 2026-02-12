import os
import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
import urllib.parse
import json

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
NAVER_ID = os.getenv("NAVER_CLIENT_ID")
NAVER_SECRET = os.getenv("NAVER_CLIENT_SECRET")

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
    return json.loads(response.choices[0].message.content)

def main():
    print("🚀 뉴스 수집 및 분석 시작...")
    query = urllib.parse.quote("데이터센터 신축 용량")
    url = f"https://openapi.naver.com/v1/search/news.json?query={query}&display=10&sort=date"
    headers = {"X-Naver-Client-Id": NAVER_ID, "X-Naver-Client-Secret": NAVER_SECRET}
    items = requests.get(url, headers=headers).json().get('items', [])

    for item in items:
        link = item['link']
        title = item['title'].replace('<b>', '').replace('</b>', '').replace('&quot;', '"')
        
        # 중복 체크
        check = supabase.table("projects").select("id").eq("url", link).execute()
        if not check.data:
            print(f"✨ 분석 중: {title}")
            body = scrape_article(link)
            if len(body) > 200:
                analysis = analyze_ai(body)
                for k in analysis:
                    if isinstance(analysis[k], list): analysis[k] = ", ".join(map(str, analysis[k]))
                analysis.update({"title": title, "url": link})
                supabase.table("projects").insert(analysis).execute()
                print(f"✅ 저장 완료")

if __name__ == "__main__":
    main()