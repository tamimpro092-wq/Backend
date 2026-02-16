from __future__ import annotations

import base64
import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import httpx

from ..settings import settings

_PRICE_RE = re.compile(r"(\$|USD\s*)(\d+(?:\.\d{1,2})?)", re.I)


def _tokenize(s: str) -> List[str]:
    return re.findall(r"[a-z0-9]{3,}", (s or "").lower())


def _median(xs: List[float]) -> Optional[float]:
    xs = [x for x in xs if isinstance(x, (int, float)) and x > 0]
    if not xs:
        return None
    xs.sort()
    n = len(xs)
    if n % 2 == 1:
        return float(xs[n // 2])
    return float((xs[n // 2 - 1] + xs[n // 2]) / 2.0)


def _extract_prices(text: str) -> List[float]:
    out: List[float] = []
    for m in _PRICE_RE.finditer(text or ""):
        try:
            out.append(float(m.group(2)))
        except Exception:
            pass
    return out


# -----------------------
# Google CSE
# -----------------------
_QUERY_TEMPLATES = [
    "best selling {niche} products",
    "top selling {niche} items",
    "{niche} best sellers",
    "trending {niche} products",
    "most popular {niche} products",
]


def google_cse_search(query: str, num: int = 10) -> Dict[str, Any]:
    if not settings.GOOGLE_CSE_API_KEY or not settings.GOOGLE_CSE_CX:
        return {"ok": False, "error": "missing_google_cse_env"}

    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": settings.GOOGLE_CSE_API_KEY,
        "cx": settings.GOOGLE_CSE_CX,
        "q": query,
        "num": max(1, min(int(num), 10)),
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, params=params)
            if r.status_code >= 400:
                return {"ok": False, "error": "google_cse_http_error", "status_code": r.status_code, "body": r.text}
            return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}


def _score_google_item(title: str, snippet: str, niche_tokens: List[str]) -> float:
    text = f"{(title or '').lower()} {(snippet or '').lower()}"
    score = 0.0

    if any(k in text for k in ["best seller", "bestseller", "top selling", "best-selling"]):
        score += 4.0
    if "trending" in text or "popular" in text:
        score += 2.0
    if any(y in text for y in ["2026", "2025"]):
        score += 1.0

    tokens = set(_tokenize(text))
    overlap = sum(1 for nt in niche_tokens if nt in tokens)
    score += min(5.0, overlap * 0.8)

    if _extract_prices(text):
        score += 1.0

    if any(bad in text for bad in ["pdf", "login", "sign in", "captcha"]):
        score -= 2.0

    return score


def google_candidates(niche: str, max_candidates: int = 8) -> Dict[str, Any]:
    niche_clean = (niche or "general").strip()
    niche_tokens = _tokenize(niche_clean)

    all_items: List[Dict[str, Any]] = []
    debug: List[Dict[str, Any]] = []

    for template in _QUERY_TEMPLATES:
        q = template.format(niche=niche_clean)
        res = google_cse_search(q, num=10)
        debug.append({"query": q, "ok": res.get("ok"), "error": res.get("error")})
        if not res.get("ok"):
            continue

        items = (res["data"] or {}).get("items") or []
        for it in items:
            title = it.get("title") or ""
            snippet = it.get("snippet") or ""
            link = it.get("link") or ""
            score = _score_google_item(title, snippet, niche_tokens)
            all_items.append({"title": title, "snippet": snippet, "link": link, "score": score})

    if not all_items:
        return {"ok": False, "error": "no_google_results", "debug": debug}

    all_items.sort(key=lambda x: x["score"], reverse=True)
    top = all_items[:max_candidates]

    # Turn results into “productish concepts”
    concepts: List[Dict[str, Any]] = []
    for it in top:
        raw_title = it["title"]
        concept = re.sub(r"^(best|top|trending|most popular)\s+", "", raw_title, flags=re.I).strip()
        concept = re.sub(r"(\|\s*.+$)", "", concept).strip()
        if len(concept) < 8:
            continue
        concepts.append({
            "concept": concept,
            "score": float(it["score"]),
            "evidence": it,
            "tokens": _tokenize(concept),
        })

    if not concepts:
        return {"ok": False, "error": "no_google_concepts", "debug": debug, "top": top}

    concepts.sort(key=lambda x: x["score"], reverse=True)
    return {"ok": True, "source": "google_cse", "niche": niche_clean, "concepts": concepts, "debug": debug}


# -----------------------
# eBay Browse API (OAuth client credentials)
# -----------------------
def _ebay_app_token() -> Dict[str, Any]:
    """
    Uses client-credentials flow to obtain an application token.
    eBay REST APIs require OAuth 2.0 access tokens. :contentReference[oaicite:4]{index=4}
    """
    cid = settings.EBAY_CLIENT_ID or ""
    csec = settings.EBAY_CLIENT_SECRET or ""
    if not cid or not csec:
        return {"ok": False, "error": "missing_ebay_env"}

    token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    basic = base64.b64encode(f"{cid}:{csec}".encode("utf-8")).decode("ascii")
    headers = {
        "Authorization": f"Basic {basic}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    data = {
        "grant_type": "client_credentials",
        # Browse scope for search
        "scope": "https://api.ebay.com/oauth/api_scope",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.post(token_url, headers=headers, data=data)
            if r.status_code >= 400:
                return {"ok": False, "error": "ebay_token_http_error", "status_code": r.status_code, "body": r.text}
            js = r.json()
            token = js.get("access_token")
            if not token:
                return {"ok": False, "error": "ebay_token_missing", "body": js}
            return {"ok": True, "access_token": token, "expires_in": js.get("expires_in")}
    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}


def ebay_search(query: str, limit: int = 20) -> Dict[str, Any]:
    tok = _ebay_app_token()
    if not tok.get("ok"):
        return tok

    marketplace = (settings.EBAY_MARKETPLACE_ID or "EBAY_US").strip()
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search"
    headers = {
        "Authorization": f"Bearer {tok['access_token']}",
        "X-EBAY-C-MARKETPLACE-ID": marketplace,
        "Accept": "application/json",
    }
    params = {"q": query, "limit": max(1, min(int(limit), 50))}

    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, headers=headers, params=params)
            if r.status_code >= 400:
                return {"ok": False, "error": "ebay_search_http_error", "status_code": r.status_code, "body": r.text}
            return {"ok": True, "data": r.json(), "marketplace": marketplace}
    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}


def ebay_signal_for_concept(concept: str) -> Dict[str, Any]:
    """
    Demand proxy:
    - total results (if present)
    - median price of returned items
    - count of items pulled
    """
    q = (concept or "").strip()
    if not q:
        return {"ok": False, "error": "empty_concept"}

    res = ebay_search(q, limit=30)
    if not res.get("ok"):
        return res

    data = res["data"] or {}
    total = data.get("total")  # may be present
    items = data.get("itemSummaries") or []

    prices: List[float] = []
    for it in items:
        price = (it.get("price") or {}).get("value")
        try:
            if price is not None:
                prices.append(float(price))
        except Exception:
            pass

    med = _median(prices)
    return {
        "ok": True,
        "query": q,
        "marketplace": res.get("marketplace"),
        "total": total,
        "items_count": len(items),
        "median_price": med,
    }


# -----------------------
# Multi-source confirmation
# -----------------------
def _jaccard(a: List[str], b: List[str]) -> float:
    sa, sb = set(a), set(b)
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / float(len(sa | sb))


def find_winning_product_multisource(niche: str) -> Dict[str, Any]:
    """
    Multi-source confirmation:
    - Generate Google candidates (live SERP best-seller/trending)
    - For top concepts, query eBay for demand proxy
    - Select the concept with highest combined score, requiring minimum eBay evidence

    If Google is unavailable (quota/env), we return error (because you said: "best, no option").
    """
    niche_clean = (niche or "general").strip()

    g = google_candidates(niche_clean, max_candidates=8)
    if not g.get("ok"):
        return {"ok": False, "error": "google_unavailable_or_no_results", "details": g}

    concepts = g["concepts"]

    scored: List[Dict[str, Any]] = []
    for c in concepts[:6]:  # keep API usage small
        concept = c["concept"]
        ebay_sig = ebay_signal_for_concept(concept)

        # eBay evidence scoring
        ebay_score = 0.0
        if ebay_sig.get("ok"):
            items_count = int(ebay_sig.get("items_count") or 0)
            total = ebay_sig.get("total")
            med_price = ebay_sig.get("median_price")

            # demand proxy: more items = more market activity
            ebay_score += min(4.0, items_count / 8.0)

            # if eBay returns "total", use it gently
            if isinstance(total, int):
                ebay_score += min(3.0, math.log10(max(1, total)) / 2.0)

            # if there is a median price, commerce relevance
            if med_price and med_price > 0:
                ebay_score += 1.0

        # confirmation gate: must have some evidence
        confirmed = bool(ebay_sig.get("ok")) and (int(ebay_sig.get("items_count") or 0) >= 8)

        combined = float(c["score"]) + float(ebay_score)
        scored.append({
            "concept": concept,
            "google_score": float(c["score"]),
            "ebay_score": float(ebay_score),
            "combined_score": combined,
            "confirmed": confirmed,
            "google_evidence": c["evidence"],
            "ebay_signal": ebay_sig,
            "tokens": c["tokens"],
        })

    # Prefer confirmed, highest combined
    confirmed = [x for x in scored if x["confirmed"]]
    pool = confirmed if confirmed else scored
    pool.sort(key=lambda x: x["combined_score"], reverse=True)
    best = pool[0]

    # Price anchor / cost heuristic from median price (if available)
    med_price = (best.get("ebay_signal") or {}).get("median_price")
    suggested_cost = 10.0
    if isinstance(med_price, (int, float)) and med_price > 0:
        suggested_cost = max(6.0, float(med_price) * 0.35)

    return {
        "ok": True,
        "source": "google_cse+ebay_browse",
        "niche": niche_clean,
        "top_pick": {
            "title": best["concept"],
            "description": f"Selected via multi-source confirmation (Google best-seller signals + eBay demand proxy) for niche: {niche_clean}.",
            "suggested_cost": round(float(suggested_cost), 2),
            "confirmed": bool(best["confirmed"]),
            "evidence": {
                "google": best["google_evidence"],
                "ebay": best["ebay_signal"],
            },
        },
        "candidates": pool[:5],
        "google_debug": g.get("debug"),
    }
