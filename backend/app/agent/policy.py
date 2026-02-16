from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from ..settings import settings
from ..schemas import ToolCall


@dataclass
class PolicyDecision:
    action: str  # allowed, needs_approval, blocked
    risk: str    # low, medium, high
    reason: str


# Tools that can cause external side-effects (require approval)
RISKY_TOOLS = (
    "shopify.publish_product",
    "facebook.create_post",
    "facebook.reply_comment",
    "facebook.reply_message",
    "whatsapp.send_reply",
    "local.write_file",
    "local.exec",
)

# ✅ Allow autopilot to run without approvals (your requirement)
ALWAYS_ALLOWED = (
    "shopify.autopilot_add_product",
)

SAFE_PREFIXES = (
    "status.",
    "research.",
    "content.",
    "supplier.",
    "call_fallback.",
)

SAFE_TOOLS = (
    "facebook.queue_posts_for_approval",
)


def evaluate(call: ToolCall, context: Dict[str, Any] | None = None) -> PolicyDecision:
    name = (call.name or "").strip()

    if name in ALWAYS_ALLOWED:
        return PolicyDecision(action="allowed", risk="high", reason="Shopify autopilot allowed")

    if name in SAFE_TOOLS:
        return PolicyDecision(action="allowed", risk="low", reason="Safe tool")

    for p in SAFE_PREFIXES:
        if name.startswith(p):
            return PolicyDecision(action="allowed", risk="low", reason="Safe tool")

    if name.startswith("local."):
        if not bool(settings.LOCAL_ACTIONS_ENABLED):
            return PolicyDecision(action="blocked", risk="high", reason="Local actions disabled")
        return PolicyDecision(action="needs_approval", risk="high", reason="Local actions require approval")

    if name in RISKY_TOOLS:
        if bool(settings.DRY_RUN):
            return PolicyDecision(
                action="needs_approval",
                risk="high",
                reason="DRY_RUN: risky action requires approval",
            )
        return PolicyDecision(action="needs_approval", risk="high", reason="Risky external action requires approval")

    return PolicyDecision(action="blocked", risk="high", reason="Unknown tool")
