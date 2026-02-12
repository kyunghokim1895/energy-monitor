# main.py의 analyze_ai 함수 부분만 아래 코드로 교체하세요.

def analyze_ai(text):
    # 위도(lat), 경도(lon)를 추가로 요청합니다.
    prompt = """
    Analyze the text as an energy analyst. Extract info in JSON format.
    Keep original language for text fields.
    Fields: 
    - project_name
    - location
    - lat (Approximate latitude of the location, float)
    - lon (Approximate longitude of the location, float)
    - power_capacity_mw
    - energy_tech
    - pue_target
    - companies
    
    If location is 'Moon' or space, set lat/lon to null.
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