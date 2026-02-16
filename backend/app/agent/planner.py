from __future__ import annotations

import re
from typing import List

from ..schemas import ToolCall


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def plan(command_text: str) -> List[ToolCall]:
    """
    Planner: convert command text into ToolCall list.

    Must support:
    - "Add a winning product and prepare it to sell"
    - "Analyze product and propose best price"
    - "Publish product 123"
    - "Create a Facebook post about product X"
    - "Reply to comment 123 with ..."
    - "Reply to message from user 999 ..."
    - "Reply on WhatsApp to 8801... with ..."
    - "Triage inbox"
    - "Generate 7 posts and queue for approval"
    - "Show me system status"
    """
    raw = _norm(command_text)
    t = raw.lower()
    calls: List[ToolCall] = []

    if any(k in t for k in ["show me system status", "system status", "status summary", "health"]):
        calls.append(ToolCall(name="status.summary", args={}))
        return calls

    if "triage inbox" in t or ("triage" in t and "inbox" in t):
        calls.append(ToolCall(name="content.triage_inbox", args={"limit": 50}))
        return calls

    m = re.search(r"\bpublish product\s+(\d+)\b", t)
    if m:
        calls.append(ToolCall(name="shopify.publish_product", args={"product_id": int(m.group(1))}))
        return calls

    if "analyze product" in t and "price" in t:
        calls.append(ToolCall(name="research.analyze_pricing", args={"mode": "latest_draft"}))
        return calls

    if "add a winning product" in t or ("winning product" in t and "prepare" in t):
        calls.append(ToolCall(name="research.find_winning_product", args={"niche": "general"}))
        calls.append(ToolCall(name="shopify.draft_product", args={"source": "research"}))
        calls.append(ToolCall(name="research.analyze_pricing", args={"mode": "latest_draft"}))
        calls.append(ToolCall(name="content.generate_product_copy", args={"mode": "latest_draft"}))
        return calls
    
    m = re.search(r"\bgenerate\s+(\d+)\s+posts\b", t)
    if m:
        n = int(m.group(1))
        calls.append(ToolCall(name="content.generate_posts_batch", args={"channel": "facebook", "count": n}))
        # publish one simple post now (batch publishing needs loop support)
        calls.append(ToolCall(name="facebook.create_post", args={"text_from": f"batch:{n}"}))
        return calls


    m = re.search(r"create a facebook post about product\s+(.+)$", raw, re.I)
    if m:
        product = m.group(1).strip()
        calls.append(ToolCall(name="content.generate_post", args={"channel": "facebook", "product": product}))
        # pass generated text into create_post using executor chaining? (simple version uses text_from only)
        calls.append(ToolCall(name="facebook.create_post", args={"text_from": f"product:{product}"}))
        return calls


    m = re.search(r"reply to comment\s+(\d+)\s+with\s+(.+)$", raw, re.I)
    if m:
        calls.append(ToolCall(name="facebook.reply_comment", args={"comment_id": m.group(1), "text": m.group(2).strip()}))
        return calls

    m = re.search(r"reply to message from user\s+(\d+)\s+(.+)$", raw, re.I)
    if m:
        calls.append(ToolCall(name="facebook.reply_message", args={"user_id": m.group(1), "text": m.group(2).strip()}))
        return calls

    m = re.search(r"reply on whatsapp to\s+([0-9\+\- ]+)\s+with\s+(.+)$", raw, re.I)
    if m:
        phone = re.sub(r"\s+", "", m.group(1))
        calls.append(ToolCall(name="whatsapp.send_reply", args={"to": phone, "text": m.group(2).strip()}))
        return calls

    m = re.search(r"\bgenerate\s+(\d+)\s+posts\b", t)
    if m:
        n = int(m.group(1))
        calls.append(ToolCall(name="content.generate_posts_batch", args={"channel": "facebook", "count": n}))
        # queue action (approval gating handled at tool/policy level)
        calls.append(ToolCall(name="facebook.queue_posts_for_approval", args={"count": n}))
        return calls

    # Default fallback: triage + summary
    calls.append(ToolCall(name="content.triage_inbox", args={"limit": 20}))
    calls.append(ToolCall(name="status.summary", args={}))
    return calls
