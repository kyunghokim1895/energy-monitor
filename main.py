# --- main.py 수정 핵심 부분 ---

# 1. 영문 키워드 추가 (글로벌 뉴스 수집용)
GLOBAL_KEYWORDS = [
    "Global Data Center Construction",
    "Hyperscale Data Center MW Capacity",
    "New Data Center Projects 2026"
]

RSS_FEEDS = [
    {"name": "DCD(Global)", "url": "https://www.datacenterdynamics.com/en/rss/"},
    {"name": "DataCenterKnowledge", "url": "https://www.datacenterknowledge.com/rss.xml"}
]

def scrape_article(url):
    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        
        # 해외 사이트 본문 태그(class, id)를 더 다양하게 탐색
        article = soup.select_one("#newsct_article") or \
                  soup.select_one(".article-body") or \
                  soup.select_one(".content-area") or \
                  soup.select_one("article") or \
                  soup.select_one(".post-content")
        
        return article.get_text(strip=True)[:3000] if article else ""
    except: return ""

# main 함수 내에서 GLOBAL_KEYWORDS 도 루프에 추가하여 검색하도록 수정