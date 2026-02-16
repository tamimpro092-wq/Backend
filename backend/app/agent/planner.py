from __future__ import annotations

import re
from typing import List
from ..schemas import ToolCall


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


_STOP = {
    "a","an","the","my","in","on","to","for","of","with","and","please",
    "shopify","store","shop","add","create","make","publish","post","put",
    "product","item","goods","selling","sell","winning","wining","best","top","hot","viral","trending",
}

# words that mean "add product"
_ADD_HINTS = (
    "add", "create", "make", "publish", "post", "put", "launch", "upload"
)

_PRODUCT_HINTS = (
    "product", "item", "goods", "sku"
)

_STORE_HINTS = (
    "shopify", "store", "shop"
)


def _extract_niche(raw: str) -> str | None:
    s = _norm(raw).lower()

    # explicit niche=...
    m = re.search(r"\bniche\s*[:=]\s*(\"[^\"]+\"|'[^']+'|[^,;\n]+)", raw, re.I)
    if m:
        v = m.group(1).strip().strip('"').strip("'").strip()
        return v or None

    # phrases like: "for summer", "for electronics", "for home decor"
    m2 = re.search(r"\bfor\s+([a-z0-9 &\-]+)", s)
    if m2:
        cand = m2.group(1)
        words = [w for w in re.findall(r"[a-z0-9]+", cand) if w and w not in _STOP]
        niche = " ".join(words).strip()
        return niche or None

    # words between add/create and product/item
    m3 = re.search(r"\b(?:add|create|make|publish|post|put)\b(.*?)(?:\bproduct\b|\bitem\b|\bgoods\b|\bsku\b)", s)
    if m3:
        cand = m3.group(1)
        words = [w for w in re.findall(r"[a-z0-9]+", cand) if w and w not in _STOP]
        niche = " ".join(words).strip()
        return niche or None

    return None


def plan(command_text: str) -> List[ToolCall]:
    raw = _norm(command_text)
    t = raw.lower()

    # status
    if any(k in t for k in ["show me system status", "system status", "status summary", "health"]):
        return [ToolCall(name="status.summary", args={})]

    # inbox
    if "triage inbox" in t or ("triage" in t and "inbox" in t):
        return [ToolCall(name="content.triage_inbox", args={"limit": 50})]

    # ✅ MAIN RULE: any "add product" intent -> autopilot
    looks_like_add_product = (
        any(h in t for h in _ADD_HINTS)
        and any(p in t for p in _PRODUCT_HINTS)
        and any(s in t for s in _STORE_HINTS)
    ) or ("wining product" in t or "winning product" in t)

    if looks_like_add_product:
        args = {}
        niche = _extract_niche(raw)
        if niche:
            args["niche"] = niche

        m_qty = re.search(r"\b(?:qty|quantity|inventory|inventory_qty)\s*[:=]\s*(\d+)", raw, re.I)
        if m_qty:
            try:
                args["inventory_qty"] = int(m_qty.group(1))
            except Exception:
                pass

        return [ToolCall(name="shopify.autopilot_add_product", args=args)]

    # fallback
    return [
        ToolCall(name="content.triage_inbox", args={"limit": 20}),
        ToolCall(name="status.summary", args={}),
    ]
