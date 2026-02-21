from __future__ import annotations

from typing import Any, Dict, List
import random
import re
import httpx

from ..settings import settings


_BAD_ALT_TOKENS = {
    "peacock", "bird", "portrait", "model", "wedding", "baby", "cat", "dog",
    "landscape", "mountain", "ocean", "sunset", "flower", "nature",
}


def _tokenize(s: str) -> List[str]:
    s = (s or "").lower()
    toks = re.findall(r"[a-z0-9]+", s)
    # drop very short tokens
    return [t for t in toks if len(t) > 2]


def _score_photo(query_tokens: List[str], photo: Dict[str, Any]) -> int:
    """
    Score a Pexels photo by overlap between query tokens and photo alt text.
    Pexels returns 'alt' in search response.
    """
    alt = (photo.get("alt") or "").lower()
    alt_tokens = set(_tokenize(alt))

    # hard reject if alt contains obvious unrelated topics
    if any(bt in alt for bt in _BAD_ALT_TOKENS):
        return -999

    # overlap score
    overlap = sum(2 for t in query_tokens if t in alt_tokens)

    # small bonus if alt contains full phrase parts like "product", "device", etc.
    bonus = 0
    if "product" in alt_tokens:
        bonus += 1
    if "device" in alt_tokens:
        bonus += 1
    if "portable" in alt_tokens:
        bonus += 1

    return overlap + bonus


def pexels_search_image(query: str, orientation: str = "square") -> Dict[str, Any]:
    """
    Returns ONE *best* matching image from Pexels (public URL), or ok=False.
    Requires: PEXELS_API_KEY

    ✅ FIX:
    - No more random.choice without relevance.
    - Score results using photo['alt'] and pick best match.
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
        "per_page": 20,                 # more choices
        "page": random.randint(1, 2),   # small randomness for variety
        "orientation": orientation,
        "size": "large",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, headers=headers, params=params)
            if r.status_code >= 400:
                return {"ok": False, "error": "pexels_http_error", "status_code": r.status_code, "body": r.text}

            data = r.json()
            photos = data.get("photos") or []
            if not photos:
                return {"ok": False, "error": "no_results", "query": q}

            query_tokens = _tokenize(q)

            # score all photos and pick best
            scored = []
            for p in photos:
                score = _score_photo(query_tokens, p)
                scored.append((score, p))

            scored.sort(key=lambda x: x[0], reverse=True)

            best_score, best = scored[0]
            if best_score < 0:
                # everything looks wrong; fail so caller can try other queries
                return {"ok": False, "error": "no_relevant_results", "query": q}

            srcs = (best.get("src") or {})
            src = srcs.get("large2x") or srcs.get("large") or srcs.get("original")
            if not src:
                return {"ok": False, "error": "no_image_url"}

            return {
                "ok": True,
                "provider": "pexels",
                "query": q,
                "image_url": src,
                "alt": best.get("alt"),
                "photographer": best.get("photographer"),
                "pexels_url": best.get("url"),
            }
    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}
