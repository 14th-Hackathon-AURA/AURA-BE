import csv
import re
from functools import lru_cache
from pathlib import Path


CATALOG_PATH = Path(__file__).resolve().parent / "data" / "mcm_products.csv"
TOKEN_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")
STOP_WORDS = {
    "그냥",
    "나한테",
    "나는",
    "내가",
    "상품",
    "제품",
    "어울리는",
    "추천",
    "추천해줘",
    "추천해주세요",
    "찾아줘",
    "찾아주세요",
    "하고",
    "해줘",
}
RECOMMENDATION_WORDS = (
    "추천",
    "골라",
    "찾아",
    "어울",
    "제품",
    "상품",
    "가방",
    "지갑",
    "스카프",
    "의류",
    "신발",
    "슈즈",
)


def _parse_price(value):
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else None


def _tokens(value):
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(str(value or ""))
        if len(token) >= 2 and token.lower() not in STOP_WORDS
    }


def _expanded_tokens(message):
    tokens = _tokens(message)
    normalized = message.lower()
    synonyms = {
        "가방": {"핸드백", "백팩", "토트백", "쇼퍼", "크로스백", "숄더백"},
        "지갑": {"지갑", "카드", "머니클립"},
        "출근": {"오피스", "비즈니스", "데일리"},
        "여행": {"트래블", "위켄더", "여행", "출장"},
        "데이트": {"데이트", "이브닝", "디너"},
        "편한": {"캐주얼", "데일리", "경량"},
    }
    for word, related in synonyms.items():
        if word in normalized:
            tokens.update(related)
    return tokens


def extract_max_budget(message):
    range_match = re.search(
        r"([0-9][0-9,]*)\s*(?:~|[-–]|에서)\s*([0-9][0-9,]*)\s*만원",
        message,
    )
    if range_match:
        return int(range_match.group(2).replace(",", "")) * 10_000

    manwon_values = re.findall(r"([0-9][0-9,]*)\s*만원", message)
    if manwon_values:
        return int(manwon_values[-1].replace(",", "")) * 10_000

    won_values = re.findall(r"([0-9][0-9,]{3,})\s*원", message)
    if won_values:
        return int(won_values[-1].replace(",", ""))
    return None


def _public_product(row):
    return {
        "style_code": row["스타일코드"],
        "name": row["상품명"],
        "gender": row["성별구분"],
        "category": row["카테고리"],
        "material": row["소재"],
        "size": row["사이즈"],
        "color": row["색상"],
        "price": row["가격"],
        "price_value": _parse_price(row["가격"]),
        "style": row["어울리는 스타일"],
        "usage": row["사용 상황"],
        "image_url": row["상품이미지"],
    }


@lru_cache(maxsize=1)
def load_catalog():
    with CATALOG_PATH.open(encoding="utf-8-sig", newline="") as catalog_file:
        return tuple(_public_product(row) for row in csv.DictReader(catalog_file))


def get_product(style_code):
    normalized = str(style_code or "").strip().upper()
    return next(
        (item for item in load_catalog() if item["style_code"].upper() == normalized),
        None,
    )


def recommend_products(message, profile=None, limit=3):
    query = str(message or "").strip()
    normalized = query.lower()
    query_tokens = _expanded_tokens(query)
    profile_tokens = set()
    profile_max_budget = None
    profile_min_budget = None

    if profile:
        profile_tokens.update(_tokens(profile.preferred_categories))
        profile_tokens.update(_tokens(profile.lifestyle))
        profile_max_budget = profile.max_budget
        profile_min_budget = profile.min_budget

    max_budget = extract_max_budget(query) or profile_max_budget
    is_recommendation = any(word in normalized for word in RECOMMENDATION_WORDS)
    scored = []

    for product in load_catalog():
        price = product["price_value"]
        if max_budget is not None and price is not None and price > max_budget:
            continue

        fields = {
            "name": product["name"].lower(),
            "category": product["category"].lower(),
            "material": product["material"].lower(),
            "color": product["color"].lower(),
            "style": product["style"].lower(),
            "usage": product["usage"].lower(),
            "gender": product["gender"].lower(),
        }
        weights = {
            "name": 8,
            "category": 6,
            "material": 4,
            "color": 5,
            "style": 5,
            "usage": 6,
            "gender": 2,
        }
        score = sum(
            weight
            for token in query_tokens
            for field, weight in weights.items()
            if token in fields[field]
        )
        score += sum(
            2
            for token in profile_tokens
            if any(token in fields[field] for field in ("category", "style", "usage"))
        )

        if profile_min_budget and price and price >= profile_min_budget:
            score += 1
        if is_recommendation:
            score += 1
        if score > 0:
            scored.append((score, price or 0, product["name"], product))

    scored.sort(key=lambda item: (-item[0], -item[1], item[2]))
    return [item[3] for item in scored[:limit]]
