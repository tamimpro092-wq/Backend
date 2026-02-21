from __future__ import annotations

from typing import Any, Dict, List, Tuple
import re
import httpx

from ..settings import settings


# Strong "avoid these" tokens (most common wrong categories)
_BAD_ALT_TOKENS = {
    "peacock", "bird", "portrait", "model", "wedding", "baby", "cat", "dog",
    "landscape", "mountain", "ocean", "sunset", "flower", "nature",
    "man", "woman", "girl", "boy", "face", "people", "person", "selfie",
    "fashion", "dress", "makeup", "hair", "smile",
}

# Tokens that are generic and should not dominate scoring
_GENERIC_TOKENS = {
    "best", "price", "cash", "delivery", "cod", "bd", "bangladesh",
    "premium", "quality", "buy", "order", "online", "shop", "store",
    "photo", "image", "product", "background", "isolated", "close", "up",
    "lifestyle", "packaging", "portable", "smart", "pro", "mini",
}

# Some simple normalization pairs so "earbuds" matches "earbud", etc.
_NORMALIZE_MAP = {
    "earbuds": "earbud",
    "headphones": "headphone",
    "earphones": "earphone",
    "speakers": "speaker",
    "bottles": "bottle",
    "fans": "fan",
    "rollers": "roller",
    "watches": "watch",
    "chargers": "charger",
    "cables": "cable",
}


def _normalize_token(t: str) -> str:
    t = t.lower().strip()
    if t in _NORMALIZE_MAP:
        return _NORMALIZE_MAP[t]
    # naive plural trim
    if len(t) > 4 and t.endswith("s"):
        return t[:-1]
    return t


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    toks = re.findall(r"[a-z0-9]+", s)
    toks = [_normalize_token(t) for t in toks if len(t) > 2]
    return toks


def _important_query_tokens(query_tokens: List[str]) -> List[str]:
    """
    Keep only meaningful product tokens from the query.
    """
    out = []
    for t in query_tokens:
        if t in _GENERIC_TOKENS:
            continue
        if t.isdigit():
            continue
        if t not in out:
            out.append(t)
    return out


def _contains_bad_topic(alt: str) -> bool:
    alt_l = (alt or "").lower()
    return any(bt in alt_l for bt in _BAD_ALT_TOKENS)


def _score_photo(query_tokens: List[str], photo: Dict[str, Any]) -> int:
    """
    Stronger scorer:
    - Requires at least 1 "important token" match, otherwise very low score.
    - Penalizes 'people/portrait/bird' type categories.
    - Rewards multiple matches and phrase/bigram-like match.
    """
    alt = (photo.get("alt") or "").lower()
    if not alt:
        return -999

    if _contains_bad_topic(alt):
        return -999

    alt_tokens = set(_tokenize(alt))
    important = _important_query_tokens(query_tokens)

    # If we have meaningful tokens, require at least one match
    if important and not any(t in alt_tokens for t in important):
        return -200

    score = 0

    # Strong weight for important token overlap
    for t in important:
        if t in alt_tokens:
            score += 6

    # Light weight for generic overlap (helps a bit but not too much)
    for t in query_tokens:
        if t in alt_tokens and t not in _GENERIC_TOKENS:
            score += 2

    # Bonus: if alt contains multiple important tokens
    if important:
        matched = sum(1 for t in important if t in alt_tokens)
        if matched >= 2:
            score += 6
        if matched >= 3:
            score += 8

    # Tiny bonus for common "product photo" hints
    if "product" in alt_tokens:
        score += 1
    if "device" in alt_tokens:
        score += 1

    return score


def pexels_search_image(query: str, orientation: str = "square") -> Dict[str, Any]:
    """
    Returns ONE best matching image from Pexels (public URL), or ok=False.
    Requires: PEXELS_API_KEY

    ✅ Fixed:
    - stable page=1 (no random weird results)
    - relevance scoring using photo['alt']
    - must-match at least one important token
    """
    api_key = getattr(settings, "PEXELS_API_KEY", "") or ""
    if not api_key:
        return {"ok": False, "error": "missing_pexels_api_key"}

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}

    params = {
        "query": q,
        "per_page": 30,         # more options to rank
        "page": 1,              # stable relevance
        "orientation": orientation,
        "size": "large",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, headers=headers, params=params)
            if r.status_code >= 400:
                return {
                    "ok": False,
                    "error": "pexels_http_error",
                    "status_code": r.status_code,
                    "body": r.text,
                }

            data = r.json() or {}
            photos = data.get("photos") or []
            if not photos:
                return {"ok": False, "error": "no_results", "query": q}

            query_tokens = _tokenize(q)

            best_score = -10_000
            best_photo = None

            for p in photos:
                s = _score_photo(query_tokens, p)
                if s > best_score:
                    best_score = s
                    best_photo = p

            if not best_photo or best_score < 0:
                return {"ok": False, "error": "no_relevant_results", "query": q}

            srcs = (best_photo.get("src") or {})
            src = srcs.get("large2x") or srcs.get("large") or srcs.get("original")
            if not src:
                return {"ok": False, "error": "no_image_url"}

            return {
                "ok": True,
                "provider": "pexels",
                "query": q,
                "image_url": src,
                "alt": best_photo.get("alt"),
                "photographer": best_photo.get("photographer"),
                "pexels_url": best_photo.get("url"),
                "score": best_score,
            }

    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}
