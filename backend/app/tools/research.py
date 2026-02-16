from __future__ import annotations

import math
import random
from typing import Any, Dict, List

from sqlmodel import Session, select

from ..db import engine
from ..models import ProductDraft


def _score_product(p: Dict[str, Any]) -> Dict[str, Any]:
    title = p.get("title", "")
    seed = sum(ord(c) for c in title) % 10000
    rng = random.Random(seed)

    demand = rng.uniform(0.40, 0.95)
    competition = rng.uniform(0.20, 0.90)
    margin = rng.uniform(0.30, 0.90)
    shipping_risk = rng.uniform(0.10, 0.80)

    score = (demand * 0.45) + ((1 - competition) * 0.25) + (margin * 0.25) + ((1 - shipping_risk) * 0.05)
    score = round(score * 100, 1)

    return {
        "score": score,
        "breakdown": {
            "demand": round(demand, 3),
            "competition": round(competition, 3),
            "margin": round(margin, 3),
            "shipping_risk": round(shipping_risk, 3),
        },
    }


def find_winning_product(niche: str = "general") -> Dict[str, Any]:
    candidates: List[Dict[str, Any]] = [
        {
            "title": "AirBrush Pro Mini Compressor",
            "description": "Compact airbrush kit for crafts and nail art with adjustable pressure.",
            "suggested_cost": 24.0,
            "niche": "beauty/crafts",
        },
        {
            "title": "Smart Posture Trainer Clip",
            "description": "Wearable posture reminder with gentle vibration and app-less usage.",
            "suggested_cost": 9.5,
            "niche": "health/fitness",
        },
        {
            "title": "Magnetic Cable Organizer Set",
            "description": "Desk cable clips with magnetic bases for clean workspace routing.",
            "suggested_cost": 4.5,
            "niche": "home/office",
        },
        {
            "title": "Portable Blender Bottle 350ml",
            "description": "USB rechargeable mini blender for shakes and smoothies, travel friendly.",
            "suggested_cost": 12.0,
            "niche": "kitchen/fitness",
        },
        {
            "title": "Pet Hair Remover Roller XL",
            "description": "Reusable lint roller for sofas and car seats; no refills needed.",
            "suggested_cost": 6.0,
            "niche": "pets/home",
        },
    ]

    ranked: List[Dict[str, Any]] = []
    for c in candidates:
        ranked.append({**c, **_score_product(c)})

    ranked.sort(key=lambda x: x["score"], reverse=True)
    top = ranked[0]

    return {
        "ok": True,
        "niche": niche,
        "top_pick": top,
        "top_5": ranked[:5],
        "method": "offline_heuristic_scoring",
    }


def analyze_pricing(mode: str = "latest_draft") -> Dict[str, Any]:
    draft = None
    with Session(engine) as session:
        if mode == "latest_draft":
            draft = session.exec(select(ProductDraft).order_by(ProductDraft.id.desc())).first()

    if not draft:
        cost = 10.0
        price = math.floor(cost * 3.2) + 0.99
        return {
            "ok": True,
            "mode": mode,
            "found_draft": False,
            "recommended_price": price,
            "currency": "USD",
            "rationale": {
                "assumed_cost": cost,
                "multiplier": 3.2,
                "psych_price": True,
                "note": "No draft found; using generic cost model.",
            },
        }

    cost = float(draft.meta.get("cost", 12.0))
    multiplier = 3.0 if cost < 10 else 2.6
    price = math.floor(cost * multiplier) + 0.99

    return {
        "ok": True,
        "mode": mode,
        "found_draft": True,
        "draft_id": draft.id,
        "recommended_price": price,
        "currency": draft.currency or "USD",
        "rationale": {
            "cost": cost,
            "multiplier": multiplier,
            "psych_price": True,
            "note": "Offline model: margin + competitive buffer.",
        },
    }
