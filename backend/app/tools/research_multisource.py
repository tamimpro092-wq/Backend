from __future__ import annotations

import random
from typing import Any, Dict, List

from ..settings import settings


# ===============================
#  ALWAYS-WORKING FALLBACK DATA
# ===============================

FALLBACK_CATALOG = {
    "beauty": [
        {
            "title": "Hydrating Hyaluronic Acid Serum",
            "description": "Lightweight daily hydration serum for smoother-looking skin.",
            "suggested_cost": 6.5,
        },
        {
            "title": "Vitamin C Brightening Face Serum",
            "description": "Brightening serum for a glowing complexion.",
            "suggested_cost": 7.2,
        },
        {
            "title": "Reusable Makeup Remover Pads (12 Pack)",
            "description": "Eco-friendly soft cleansing pads for daily use.",
            "suggested_cost": 4.1,
        },
        {
            "title": "Dermaplaning Facial Razor Set (6 Pack)",
            "description": "Precision razors for smoother makeup application.",
            "suggested_cost": 3.8,
        },
    ],
    "general": [
        {
            "title": "LED Motion Sensor Night Light (2 Pack)",
            "description": "Automatic night light for hallway, closet and stairs.",
            "suggested_cost": 5.5,
        },
        {
            "title": "Portable Mini Blender Bottle",
            "description": "Compact mixer bottle for smoothies and protein shakes.",
            "suggested_cost": 8.0,
        },
    ],
}


def _pick_fallback(niche: str) -> Dict[str, Any]:
    niche = (niche or "general").strip().lower()
    if niche not in FALLBACK_CATALOG:
        niche = "general"

    item = random.choice(FALLBACK_CATALOG[niche])

    return {
        "ok": True,
        "chosen_niche": niche,
        "sources_used": ["fallback_catalog"],
        "top_pick": {
            "title": item["title"],
            "description": item["description"],
            "suggested_cost": item["suggested_cost"],
            "source": "fallback_catalog",
            "confirmed": False,
        },
    }


# ===============================
#  MAIN MULTI-SOURCE FUNCTION
# ===============================

def find_winning_product_multisource(niche: str = "general") -> Dict[str, Any]:
    """
    This version NEVER fails.
    It always returns a valid product.
    """

    niche = (niche or "general").strip()

    # If in future you re-add Google/eBay logic,
    # it can go here — but must NEVER hard fail.

    return _pick_fallback(niche)


def find_winning_product_multisource_for_many(niches: List[str]) -> Dict[str, Any]:
    niches = [n.strip() for n in (niches or []) if n and n.strip()]
    if not niches:
        return find_winning_product_multisource("general")

    return find_winning_product_multisource(niches[0])
