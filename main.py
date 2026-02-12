# --- main.py 내 analyze_ai 함수 부분만 수정 ---

def analyze_ai(text):
    # 2번 해결: 원문 언어를 유지하도록 프롬프트 변경
    prompt = """
    너는 글로벌 에너지 분석가야. 다음 텍스트에서 정보를 추출해 JSON으로 응답해.
    중요: 기사가 영어라면 영어로, 한국어라면 한국어로, 기사 원문의 언어를 그대로 유지해서 추출해. (번역하지 마)
    필드: project_name, location, power_capacity_mw, energy_tech, pue_target, companies. 
    정보가 없으면 null로 표시해.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": prompt}, {"role": "user", "content": text}],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except: return None