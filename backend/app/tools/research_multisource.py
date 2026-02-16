from __future__ import annotations

import random
from typing import Any, Dict, List

from ..settings import settings

# ✅ Always-working fallback products (so autopilot never breaks)
FALLBACK_CATALOG = {
    "beauty": [
        {
            "title": "Hydrating Hyaluronic Acid Serum",
            "description": "Lightweight daily hydration serum for smoother-looking skin.",
            "suggested_cost": 6.5,
        },
        {
            "title": "Vitamin C Brightening Face Serum",
            "description": "Brightening serum for an even-looking glow.",
            "suggested_cost": 7.2,
        },
        {
            "title": "Reusable Makeup Remover Pads (12 Pack)",
            "description": "Soft reusable pads for gentle cleansing and makeup removal.",
            "suggested_cost": 4.1,
        },
        {
            "title": "Dermaplaning Facial Razor Set (6 Pack)",
            "description": "Facial razors for smoother makeup application.",
            "suggested_cost": 3.8,
        },
    ],
    "general": [
        {
            "title": "LED Motion Sensor Night Light (2 Pack)",
            "description": "Auto on/off night lights for hallway, closet, and stairs.",
            "suggested_cost": 5.5,
        },
        {
            "title": "Portable Mini Blender Bottle",
            "description": "Compact everyday mixer bottle for shakes and smoothies.",
            "suggested_cost": 8.0,
        },
    ],
}


def _pick_fallback(niche: str) -> Dict[str, Any]:
    n = (niche or "general").strip().lower()
    if n not in FALLBACK_CATALOG:
        n = "general"
    item = random.choice(FALLBACK_CATALOG[n])

    return {
        "ok": True,
        "chosen_niche": n,
        "sources_used": ["fallback_catalog"],
        "top_pick": {
            "title": item["title"],
            "description": item["description"],
            "suggested_cost": item["suggested_cost"],
            "source": "fallback_catalog",
            "confirmed": False,
        },
    }


def find_winning_product_multisource(niche: str = "general") -> Dict[str, Any]:
    """
    Robust research:
    - Try Google CSE if configured
    - Try eBay if configured
    - If both fail → fallback catalog (never fails)
    """
    n = (niche or "general").strip()

    # 1) Google CSE (only if keys exist)
    has_google = bool(getattr(settings, "GOOGLE_CSE_API_KEY", "")) and bool(getattr(settings, "GOOGLE_CSE_CX", ""))
    if has_google:
        try:
            from .research_google import google_find_winning_product

            g = google_find_winning_product(niche=n)
            if g and g.get("ok"):
                g["chosen_niche"] = n
                g["sources_used"] = list(dict.fromkeys((g.get("sources_used") or []) + ["google"]))
                return g
        except Exception:
            pass

    # 2) eBay (only if keys exist)
    has_ebay = bool(getattr(settings, "EBAY_CLIENT_ID", "")) and bool(getattr(settings, "EBAY_CLIENT_SECRET", ""))
    if has_ebay:
        try:
            from .research_ebay import ebay_find_winning_product

            e = ebay_find_winning_product(niche=n)
            if e and e.get("ok"):
                e["chosen_niche"] = n
                e["sources_used"] = list(dict.fromkeys((e.get("sources_used") or []) + ["ebay"]))
                return e
        except Exception:
            pass

    # 3) Always works fallback
    return _pick_fallback(n)


def find_winning_product_multisource_for_many(niches: List[str]) -> Dict[str, Any]:
    niches = [x.strip() for x in (niches or []) if x and x.strip()]
    if not niches:
        return find_winning_product_multisource("general")

    for n in niches:
        r = find_winning_product_multisource(n)
        if r.get("ok"):
            r["chosen_niche"] = r.get("chosen_niche") or n
            return r

    return _pick_fallback(niches[0])
