from __future__ import annotations

from typing import Any, Dict
import random
import httpx

from ..settings import settings


def pexels_search_image(query: str, orientation: str = "square") -> Dict[str, Any]:
    """
    Returns one image from Pexels (public URL), or ok=False.
    Requires: PEXELS_API_KEY

    Updated:
    - per_page=10 (not 1)
    - random pick to avoid repeating same photo
    """
    api_key = getattr(settings, "PEXELS_API_KEY", "") or ""
    if not api_key:
        return {"ok": False, "error": "missing_pexels_api_key"}

    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "empty_query"}

    url = "https://api.pexels.com/v1/search"
    headers = {"Authorization": api_key}

    # pull more options so we can choose a better one + avoid repeats
    params = {
        "query": q,
        "per_page": 10,
        "page": random.randint(1, 3),
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

            p = random.choice(photos)
            srcs = (p.get("src") or {})
            src = srcs.get("large2x") or srcs.get("large") or srcs.get("original")

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
