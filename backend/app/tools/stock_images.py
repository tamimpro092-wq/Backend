from __future__ import annotations

from typing import Any, Dict
import httpx

from ..settings import settings


def pexels_search_image(query: str, orientation: str = "square") -> Dict[str, Any]:
    """
    Returns one best image from Pexels (public URL), or ok=False.
    Requires: PEXELS_API_KEY
    """
    api_key = getattr(settings, "PEXELS_API_KEY", "") or ""
    if not api_key:
        return {"ok": False, "error": "missing_pexels_api_key"}

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}
    params = {"query": q, "per_page": 1, "orientation": orientation, "size": "large"}

    try:
        with httpx.Client(timeout=20.0) as client:
            r = client.get(url, headers=headers, params=params)
            if r.status_code >= 400:
                return {"ok": False, "error": "pexels_http_error", "status_code": r.status_code, "body": r.text}

            data = r.json()
            photos = data.get("photos") or []
            if not photos:
                return {"ok": False, "error": "no_results", "query": q}

            p = photos[0]
            src = (p.get("src") or {}).get("large2x") or (p.get("src") or {}).get("large") or (p.get("src") or {}).get("original")
            if not src:
                return {"ok": False, "error": "no_image_url"}

            return {
                "ok": True,
                "provider": "pexels",
                "query": q,
                "image_url": src,
                "photographer": p.get("photographer"),
                "pexels_url": p.get("url"),
            }
    except Exception as e:
        return {"ok": False, "error": "exception", "message": str(e)}
