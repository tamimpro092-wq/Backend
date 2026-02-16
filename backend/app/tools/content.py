from __future__ import annotations

from typing import Any, Dict, List, Optional

from sqlmodel import Session, select

from ..db import engine
from ..models import MessageEvent, ProductDraft
from ..settings import settings
from .llm import generate


def triage_inbox(limit: int = 50) -> Dict[str, Any]:
    with Session(engine) as session:
        msgs = session.exec(select(MessageEvent).order_by(MessageEvent.id.desc()).limit(limit)).all()

    buckets = {"order": [], "refund": [], "general": []}
    for m in msgs:
        t = (m.text or "").lower()
        row = {"id": m.id, "channel": m.channel, "from": m.from_user, "text": m.text}
        if any(k in t for k in ["order", "shipping", "delivery", "where"]):
            buckets["order"].append(row)
        elif any(k in t for k in ["refund", "return", "money back"]):
            buckets["refund"].append(row)
        else:
            buckets["general"].append(row)

    return {"ok": True, "limit": limit, "counts": {k: len(v) for k, v in buckets.items()}, "buckets": buckets}


def draft_reply(channel: str, from_user: str, text: str, brand: Optional[str]) -> Dict[str, Any]:
    brand_name = brand or settings.BRAND_NAME
    out = generate(brand=brand_name, user_text=text, channel=channel)
    return {"ok": True, "channel": channel, "to": from_user, "text": out["text"], "provider": out["provider"]}


def generate_post(channel: str = "facebook", product: str = "Product") -> Dict[str, Any]:
    brand = settings.BRAND_NAME
    # Still includes required phrase exactly once.
    text = f"I'm the AI assistant for {brand}. New drop: {product}. Limited stock—tap to shop and DM your order number if you need help."
    return {"ok": True, "channel": channel, "text": text, "product": product}


def generate_posts_batch(channel: str = "facebook", count: int = 7) -> Dict[str, Any]:
    brand = settings.BRAND_NAME
    posts: List[Dict[str, Any]] = []
    for i in range(count):
        posts.append(
            {
                "idx": i + 1,
                "text": f"I'm the AI assistant for {brand}. Post #{i+1}: New arrivals today—grab yours before it’s gone. Need help? Share your order number.",
            }
        )
    return {"ok": True, "channel": channel, "count": count, "posts": posts}


def generate_product_copy(mode: str = "latest_draft") -> Dict[str, Any]:
    with Session(engine) as session:
        draft = session.exec(select(ProductDraft).order_by(ProductDraft.id.desc())).first()

    if not draft:
        return {"ok": True, "found_draft": False, "title": "", "description": "No draft found."}

    bullets = [
        "✅ Compact and easy to use",
        "✅ Great for beginners and pros",
        "✅ Fast setup, consistent results",
        "✅ Perfect for gifts and daily use",
    ]
    enhanced = (
        f"{draft.description}\n\nHighlights:\n"
        + "\n".join(bullets)
        + "\n\nSupport: For order questions, ask for the order number."
    )
    return {"ok": True, "found_draft": True, "draft_id": draft.id, "title": draft.title, "enhanced_description": enhanced}
