"""
뉴스 텍스트에서 사상자 정보를 자동 추출하는 모듈

패턴 매칭 기반 — LLM 사용 없음
"killed 12", "3 dead", "at least 25 people were killed" 등의 패턴 인식
"""
import re

# 숫자 텍스트 → 정수 변환
_WORD_TO_NUM = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
    "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
    "eighty": 80, "ninety": 90, "hundred": 100, "dozens": 24, "scores": 40,
}

# 사망 패턴 (영어)
_KILL_PATTERNS = [
    # "kill 12", "kills 12", "killed 25", "killing 3"
    r'(?:kill(?:s|ed|ing)?)\s+(?:at\s+least\s+)?(\d+)',
    # "12 killed", "25 dead", "3 slain"
    r'(\d+)\s+(?:people\s+)?(?:killed|dead|slain|martyred|massacred)',
    # "death toll rises to 45"
    r'death\s+toll\s+(?:rises?\s+to|reaches?|hits?|stands?\s+at)\s+(\d+)',
    # "claimed the lives of 12"
    r'claimed?\s+(?:the\s+)?lives?\s+of\s+(\d+)',
    # "left 8 dead"
    r'left\s+(\d+)\s+(?:people\s+)?dead',
    # "at least 15 people were killed"
    r'at\s+least\s+(\d+)\s+(?:people\s+)?(?:were\s+)?killed',
    # "12 soldiers killed"
    r'(\d+)\s+(?:soldiers?|troops?|militants?|civilians?|people|persons?|policem[ae]n|officers?)\s+(?:were\s+)?(?:killed|dead|slain)',
    # "kills at least 20"
    r'kills?\s+at\s+least\s+(\d+)',
    # "murdered 5"
    r'murdered?\s+(\d+)',
    # word numbers: "killed twelve"
    r'(?:kill(?:s|ed|ing))\s+(?:at\s+least\s+)?({words})',
    # "three killed", "three soldiers killed"
    r'({words})\s+(?:\w+\s+)?(?:killed|dead|slain)',
]

# 부상 패턴
_WOUND_PATTERNS = [
    r'(\d+)\s+(?:people\s+)?(?:wounded|injured|hurt)',
    r'(?:wound(?:s|ed|ing)|injur(?:es?|ed|ing))\s+(?:at\s+least\s+)?(\d+)',
    r'at\s+least\s+(\d+)\s+(?:people\s+)?(?:were\s+)?(?:wounded|injured)',
    r'(\d+)\s+(?:soldiers?|troops?|civilians?|people|policem[ae]n|officers?)\s+(?:were\s+)?(?:wounded|injured)',
    r'({words})\s+(?:\w+\s+)?(?:wounded|injured|hurt)',
]

# 숫자 단어 패턴 생성
_word_pattern = "|".join(_WORD_TO_NUM.keys())
_KILL_PATTERNS = [p.format(words=_word_pattern) if "{words}" in p else p for p in _KILL_PATTERNS]
_WOUND_PATTERNS = [p.format(words=_word_pattern) if "{words}" in p else p for p in _WOUND_PATTERNS]


def _parse_number(s: str) -> int:
    """숫자 문자열 또는 영어 단어를 정수로 변환"""
    s = s.strip().lower()
    if s.isdigit():
        return int(s)
    return _WORD_TO_NUM.get(s, 0)


def extract_casualties(text: str) -> dict:
    """
    텍스트에서 사상자 정보 추출

    Returns:
        {
            "fatalities_estimated": int,  # 추정 사망자
            "wounded_estimated": int,     # 추정 부상자
            "confidence": str,            # HIGH/MEDIUM/LOW
            "matches": list[str],         # 매칭된 원문 구절
        }
    """
    if not text:
        return {"fatalities_estimated": 0, "wounded_estimated": 0, "confidence": "NONE", "matches": []}

    text_lower = text.lower()
    fatalities = []
    wounded = []
    matches = []

    # 사망자 추출
    for pattern in _KILL_PATTERNS:
        for m in re.finditer(pattern, text_lower):
            num_str = m.group(1)
            num = _parse_number(num_str)
            if 0 < num < 10000:  # 합리적 범위
                fatalities.append(num)
                # 원문에서 매칭된 부분 추출
                start = max(0, m.start() - 10)
                end = min(len(text), m.end() + 10)
                matches.append(text[start:end].strip())

    # 부상자 추출
    for pattern in _WOUND_PATTERNS:
        for m in re.finditer(pattern, text_lower):
            num_str = m.group(1)
            num = _parse_number(num_str)
            if 0 < num < 10000:
                wounded.append(num)

    # 가장 큰 값을 채택 (보통 같은 사건의 다른 표현)
    best_fatal = max(fatalities) if fatalities else 0
    best_wound = max(wounded) if wounded else 0

    # 신뢰도 판단
    if len(fatalities) >= 2:
        confidence = "HIGH"  # 여러 패턴에서 확인
    elif len(fatalities) == 1:
        confidence = "MEDIUM"
    else:
        confidence = "NONE"

    return {
        "fatalities_estimated": best_fatal,
        "wounded_estimated": best_wound,
        "confidence": confidence,
        "matches": matches[:3],
    }


def enrich_articles_with_casualties(articles: list[dict]) -> list[dict]:
    """
    뉴스 기사 리스트에 사상자 추정치를 추가

    각 기사의 title + summary에서 사상자를 추출하여
    fatalities_estimated, wounded_estimated, casualty_confidence 필드 추가
    """
    for article in articles:
        text = f"{article.get('title', '')} {article.get('summary', '')}"
        result = extract_casualties(text)
        article["fatalities_estimated"] = result["fatalities_estimated"]
        article["wounded_estimated"] = result["wounded_estimated"]
        article["casualty_confidence"] = result["confidence"]
        article["casualty_matches"] = result["matches"]
    return articles
