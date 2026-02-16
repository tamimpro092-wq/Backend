from __future__ import annotations

import re
from typing import List
from ..schemas import ToolCall


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def plan(command_text: str) -> List[ToolCall]:
    raw = _norm(command_text)
    t = raw.lower()
    calls: List[ToolCall] = []

    if any(k in t for k in ["show me system status", "system status", "status summary", "health"]):
        return [ToolCall(name="status.summary", args={})]

    if "triage inbox" in t or ("triage" in t and "inbox" in t):
        return [ToolCall(name="content.triage_inbox", args={"limit": 50})]

    # ✅ Shopify autopilot (one command)
    if any(
        k in t
        for k in [
            "add a product in my store",
            "add product in my store",
            "create a product in my store",
            "create product in my store",
            "add a product",
            "add product",
        ]
    ):
        args = {}

        m_niche = re.search(r"\bniche\s*[:=]\s*(\"[^\"]+\"|'[^']+'|[^,;\n]+)", raw, re.I)
        if m_niche:
            niche_val = m_niche.group(1).strip().strip('"').strip("'").strip()
            if niche_val:
                args["niche"] = niche_val

        m_qty = re.search(r"\b(?:qty|quantity|inventory|inventory_qty)\s*[:=]\s*(\d+)", raw, re.I)
        if m_qty:
            try:
                args["inventory_qty"] = int(m_qty.group(1))
            except Exception:
                pass

        return [ToolCall(name="shopify.autopilot_add_product", args=args)]

    m = re.search(r"\bpublish product\s+(\d+)\b", t)
    if m:
        return [ToolCall(name="shopify.publish_product", args={"product_id": int(m.group(1))})]

    if "analyze product" in t and "price" in t:
        return [ToolCall(name="research.analyze_pricing", args={"mode": "latest_draft"})]

    if "add a winning product" in t or ("winning product" in t and "prepare" in t):
        return [
            ToolCall(name="research.find_winning_product", args={"niche": "general"}),
            ToolCall(name="shopify.draft_product", args={"source": "research"}),
            ToolCall(name="research.analyze_pricing", args={"mode": "latest_draft"}),
            ToolCall(name="content.generate_product_copy", args={"mode": "latest_draft"}),
        ]

    # ✅ keep ONLY ONE generate posts handler (choose approval queue or create immediately)
    m = re.search(r"\bgenerate\s+(\d+)\s+posts\b", t)
    if m:
        n = int(m.group(1))
        return [
            ToolCall(name="content.generate_posts_batch", args={"channel": "facebook", "count": n}),
            ToolCall(name="facebook.queue_posts_for_approval", args={"count": n}),
        ]

    m = re.search(r"create a facebook post about product\s+(.+)$", raw, re.I)
    if m:
        product = m.group(1).strip()
        return [
            ToolCall(name="content.generate_post", args={"channel": "facebook", "product": product}),
            ToolCall(name="facebook.create_post", args={"text_from": f"product:{product}"}),
        ]

    m = re.search(r"reply to comment\s+(\d+)\s+with\s+(.+)$", raw, re.I)
    if m:
        return [ToolCall(name="facebook.reply_comment", args={"comment_id": m.group(1), "text": m.group(2).strip()})]

    m = re.search(r"reply to message from user\s+(\d+)\s+(.+)$", raw, re.I)
    if m:
        return [ToolCall(name="facebook.reply_message", args={"user_id": m.group(1), "text": m.group(2).strip()})]

    m = re.search(r"reply on whatsapp to\s+([0-9\+\- ]+)\s+with\s+(.+)$", raw, re.I)
    if m:
        phone = re.sub(r"\s+", "", m.group(1))
        return [ToolCall(name="whatsapp.send_reply", args={"to": phone, "text": m.group(2).strip()})]

    return [
        ToolCall(name="content.triage_inbox", args={"limit": 20}),
        ToolCall(name="status.summary", args={}),
    ]
