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


RISKY_TOOLS = (
    "shopify.publish_product",
    "facebook.create_post",
    "facebook.reply_comment",
    "facebook.reply_message",
    "whatsapp.send_reply",
    "local.write_file",
    "local.exec",
)

# ✅ Allow Shopify autopilot to run (no approvals)
ALWAYS_ALLOWED = (
    "shopify.autopilot_add_product",
)

SAFE_PREFIXES = (
    "status.",
    "research.",
    "content.",
    "supplier.",
    "call_fallback.",
    "facebook.queue_posts_forưA
    "facebook.queue_posts_for_approval",
)


def evaluate(call: ToolCall, context: Dict[str, Any] | None = None) -> PolicyDecision:
    name = call.name or ""

    # ✅ allow this tool to execute
    if name in ALWAYS_ALLOWED:
        return PolicyDecision(action="allowed", risk="high", reason="Shopify autopilot allowed")

    if name.startswith(SAFE_PREFIXES):
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
                reason="DRY_RUN: risky action requires approval (simulated if approved)",
            )
        return PolicyDecision(action="needs_approval", risk="high", reason="Risky external action requires approval")

    return PolicyDecision(action="blocked", risk="high", reason="Unknown tool")
