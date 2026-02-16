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

    # ✅ Your Mira voice command (typo tolerant)
    if any(k in t for k in ["wining product", "winning product"]) and "shopify" in t and ("store" in t or "shop" in t):
        return [ToolCall(name="shopify.autopilot_add_product", args={})]

    # ✅ Shopify autopilot one command
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

    # Keep safe fallback
    return [
        ToolCall(name="content.triage_inbox", args={"limit": 20}),
        ToolCall(name="status.summary", args={}),
    ]
