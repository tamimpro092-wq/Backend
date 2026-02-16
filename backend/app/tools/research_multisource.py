from __future__ import annotations

import random
import re
from typing import Any, Dict, List, Tuple

from sqlmodel import Session, select

from ..db import engine
from ..models import ProductDraft


CATALOG: Dict[str, List[Dict[str, Any]]] = {
    "electronics": [
        {"base": "Smart Tag Key Finder (Bluetooth)", "desc": "Track keys, wallets, and bags with a compact Bluetooth tracker.", "cost": (250, 550)},
        {"base": "Magnetic Phone Car Mount", "desc": "Strong magnetic mount for safer hands-free navigation.", "cost": (180, 450)},
        {"base": "USB-C Fast Charger (20W)", "desc": "Fast, safe charging for phones and small devices.", "cost": (220, 520)},
        {"base": "Foldable Phone Stand", "desc": "Adjustable stand for desk viewing, calls, and videos.", "cost": (120, 350)},
        {"base": "Cable Organizer Clips (12 Pack)", "desc": "Keep your cables neat, tidy, and easy to reach.", "cost": (90, 220)},
    ],
    "home decor": [
        {"base": "Stretch Sofa Cover (Washable)", "desc": "Upgrade your old sofa in minutes with a premium stretch cover.", "cost": (900, 1500)},
        {"base": "LED Motion Sensor Night Light (2 Pack)", "desc": "Automatic night light for hallway, closet, and stairs.", "cost": (350, 700)},
        {"base": "Minimalist Wall Hooks Set", "desc": "Strong wall hooks for keys, bags, and essentials.", "cost": (250, 600)},
        {"base": "Decorative Cushion Cover (18x18)", "desc": "Refresh your living room instantly with premium cushion covers.", "cost": (250, 550)},
    ],
    "kitchen": [
        {"base": "Oil Spray Bottle", "desc": "Fine mist sprayer for healthier and even cooking.", "cost": (250, 600)},
        {"base": "Sink Caddy Organizer", "desc": "Keep sponge/brush tidy and dry in your kitchen sink.", "cost": (220, 520)},
        {"base": "Reusable Food Storage Bags (Set of 4)", "desc": "Leak-resistant reusable bags for snacks and meal prep.", "cost": (450, 950)},
    ],
    "beauty": [
        {"base": "Vitamin C Brightening Face Serum", "desc": "Glow-boosting skincare serum for brighter-looking skin.", "cost": (350, 800)},
        {"base": "Hyaluronic Acid Hydrating Serum", "desc": "Daily hydration serum for smoother-looking skin.", "cost": (350, 800)},
        {"base": "Reusable Makeup Remover Pads (12 Pack)", "desc": "Soft reusable pads for gentle cleansing and makeup removal.", "cost": (180, 450)},
    ],
    "fitness": [
        {"base": "Resistance Bands Set (5 Levels)", "desc": "Workout bands set for home gym training.", "cost": (450, 950)},
        {"base": "Adjustable Jump Rope", "desc": "Smooth jump rope for cardio workouts at home.", "cost": (250, 600)},
    ],
    "summer": [
        {"base": "Cooling Towel (Sports)", "desc": "Instant cooling towel for summer heat and workouts.", "cost": (180, 450)},
        {"base": "Waterproof Phone Pouch", "desc": "Protect your phone at beach, rain, and travel.", "cost": (200, 520)},
        {"base": "UV Protection Sunglasses", "desc": "Stylish UV sunglasses for daily outdoor use.", "cost": (250, 650)},
    ],
    "general": [
        {"base": "Portable Mini Blender Bottle", "desc": "Compact mixer bottle for smoothies and protein shakes.", "cost": (350, 850)},
        {"base": "Anti-Slip Drawer Liner", "desc": "Non-adhesive liner to keep items in place.", "cost": (220, 520)},
    ],
}

ADJ = ["Premium", "Pro", "Ultra", "Smart", "Compact", "Portable", "Modern", "Heavy-Duty"]
BENEFITS = [
    "High demand + easy to sell",
    "Gift-friendly product",
    "Lightweight and easy to ship",
    "Great for COD customers",
    "Strong repeat-purchase potential",
]


def _norm_niche(niche: str) -> str:
    s = (niche or "general").strip().lower()
    s = s.replace("&", "and")
    s = re.sub(r"\s+", " ", s)
    mapping = {
        "tech": "electronics",
        "gadgets": "electronics",
        "decor": "home decor",
        "home decoration": "home decor",
        "sofa": "home decor",
        "kitchenware": "kitchen",
        "gym": "fitness",
        "workout": "fitness",
    }
    return mapping.get(s, s)


def _recent_titles(limit: int = 80) -> List[str]:
    try:
        with Session(engine) as session:
            rows = session.exec(
                select(ProductDraft.title).order_by(ProductDraft.created_at.desc()).limit(limit)
            ).all()
            return [r for r in rows if r]
    except Exception:
        return []


def _pick_unique(niche_key: str) -> Dict[str, Any]:
    niche_key = _norm_niche(niche_key)
    if niche_key not in CATALOG:
        niche_key = "general"

    recent = set(t.lower().strip() for t in _recent_titles(80))
    pool = CATALOG[niche_key]

    for _ in range(40):
        item = random.choice(pool)
        base = item["base"].strip()

        title = base
        if random.random() < 0.55:
            title = f"{random.choice(ADJ)} {base}"

        if title.lower() in recent:
            continue

        lo, hi = item["cost"]
        cost = float(random.randint(int(lo), int(hi)))

        return {
            "title": title,
            "description": item["desc"].strip(),
            "suggested_cost": cost,
            "niche_key": niche_key,
            "signals": random.sample(BENEFITS, k=3),
        }

    # last fallback
    item = random.choice(pool)
    lo, hi = item["cost"]
    return {
        "title": f"{random.choice(ADJ)} {item['base']}",
        "description": item["desc"].strip(),
        "suggested_cost": float(random.randint(int(lo), int(hi))),
        "niche_key": niche_key,
        "signals": random.sample(BENEFITS, k=3),
    }


def find_winning_product_multisource(niche: str = "general") -> Dict[str, Any]:
    top = _pick_unique(niche)
    return {
        "ok": True,
        "chosen_niche": top["niche_key"],
        "sources_used": ["internal_catalog"],
        "top_pick": {
            "title": top["title"],
            "description": top["description"],
            "suggested_cost": top["suggested_cost"],
            "source": "internal_catalog",
            "confirmed": False,
        },
        "market_signals": top.get("signals", []),
    }


def find_winning_product_multisource_for_many(niches: List[str]) -> Dict[str, Any]:
    niches = [x.strip() for x in (niches or []) if x and x.strip()]
    if not niches:
        return find_winning_product_multisource("general")
    return find_winning_product_multisource(random.choice(niches))
