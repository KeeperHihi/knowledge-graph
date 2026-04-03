import re
import unicodedata


def normalize_text(text: str) -> str:
    # 统一大小写、全半角和符号，便于中英文混合匹配
    normalized = unicodedata.normalize("NFKC", text).lower()
    normalized = normalized.replace("·", "").replace("•", "")
    normalized = re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)
    return normalized


def split_tokens(text: str) -> list[str]:
    return re.findall(r"[A-Za-z]+|[\u4e00-\u9fff]+|\d+", text.lower())


def token_overlap_ratio(text_a: str, text_b: str) -> float:
    tokens_a = set(split_tokens(text_a))
    tokens_b = set(split_tokens(text_b))
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = len(tokens_a & tokens_b)
    union = len(tokens_a | tokens_b)
    return intersection / union if union else 0.0


def keyword_hit_score(context: str, keywords: list[str]) -> float:
    if not keywords:
        return 0.0

    context_lower = context.lower()
    context_norm = normalize_text(context)
    hits = 0

    for keyword in keywords:
        keyword_lower = keyword.lower()
        keyword_norm = normalize_text(keyword)
        if keyword_lower and keyword_lower in context_lower:
            hits += 1
        elif keyword_norm and keyword_norm in context_norm:
            hits += 1

    # 两个关键词命中就视为上下文证据足够强
    return min(1.0, hits / max(1, min(2, len(keywords))))
