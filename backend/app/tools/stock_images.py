from __future__ import annotations

from typing import Any, Dict, List
import re
import httpx

from ..settings import settings


_BAD_TOKENS = {
    # animals / nature
    "peacock", "bird", "animal", "cat", "dog", "flower", "nature", "landscape",
    "mountain", "ocean", "sunset",
    # people / fashion
    "portrait", "model", "wedding", "baby", "man", "woman", "girl", "boy",
    "people", "person", "selfie", "fashion", "dress", "makeup", "hair", "smile",
    # jewelry (your screenshots issue)
    "ring", "bracelet", "necklace", "jewelry", "diamond", "gold", "silver",
    # random wrong tech that appears a lot
    "camera", "controller", "console", "gaming",
}

_GENERIC_TOKENS = {
    "best", "price", "cash", "delivery", "cod", "bd", "bangladesh",
    "premium", "quality", "buy", "order", "online", "shop", "store",
    "photo", "image", "product", "background", "isolated", "close", "up",
    "lifestyle", "packaging", "portable", "smart", "pro", "mini",
}

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
    if len(t) > 4 and t.endswith("s"):
        return t[:-1]
    return t


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    toks = re.findall(r"[a-z0-9]+", s)
    toks = [_normalize_token(t) for t in toks if len(t) > 2]
    return toks


def _important_query_tokens(query_tokens: List[str]) -> List[str]:
    out: List[str] = []
    for t in query_tokens:
        if t in _GENERIC_TOKENS:
            continue
        if t.isdigit():
            continue
        if t not in out:
            out.append(t)
    return out


def _looks_wrong(text: str) -> bool:
    s = (text or "").lower()
    return any(bt in s for bt in _BAD_TOKENS)


def _score_photo(query_tokens: List[str], photo: Dict[str, Any]) -> int:
    """
    Scoring rules:
    - If ALT exists, score by token overlap.
    - If ALT is empty, don't auto-reject (score low) because Pexels sometimes has empty ALT.
    - Hard reject if ALT contains bad topics (jewelry/people/birds/gaming).
    """
    alt = (photo.get("alt") or "").lower()

    # Hard reject obviously wrong topics (only if we have alt)
    if alt and _looks_wrong(alt):
        return -999

    alt_tokens = set(_tokenize(alt))
    important = _important_query_tokens(query_tokens)

    # If alt is missing, allow but score low so it's used only as fallback
    if not alt:
        return 1

    # Require at least one important match when possible
    if important and not any(t in alt_tokens for t in important):
        return -100

    score = 0

    for t in important:
        if t in alt_tokens:
            score += 7

    # small bonus for extra matches
    matched = sum(1 for t in important if t in alt_tokens)
    if matched >= 2:
        score += 6
    if matched >= 3:
        score += 8

    # small helpful bonus words
    if "product" in alt_tokens:
        score += 1
    if "device" in alt_tokens:
        score += 1

    return score


def pexels_search_image(query: str, orientation: str = "square") -> Dict[str, Any]:
    """
    Returns ONE best matching image from Pexels (public URL), or ok=False.

    ✅ Fixes:
    - stable page=1
    - score results by relevance
    - does NOT fail only because ALT is empty
    - rejects obvious wrong topics
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
        "per_page": 40,
        "page": 1,
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
                # also check url text; helps block wrong stuff even if alt weak
                url_text = (p.get("url") or "") + " " + str((p.get("src") or {}).get("original") or "")
                if _looks_wrong(url_text):
                    continue

                s = _score_photo(query_tokens, p)
                if s > best_score:
                    best_score = s
                    best_photo = p

            if not best_photo:
                return {"ok": False, "error": "no_relevant_results", "query": q}

            srcs = (best_photo.get("src") or {})
            src = srcs.get("large2x") or srcs.get("large") or srcs.get("original")
            if not src:
                return {"ok": False, "error": "no_image_url"}

            # If score is extremely low AND alt exists and looks wrong, fail
            alt = best_photo.get("alt") or ""
            if best_score < 0 and alt and _looks_wrong(alt):
                return {"ok": False, "error": "no_relevant_results", "query": q}

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
