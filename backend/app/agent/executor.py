from __future__ import annotations

import logging
from typing import Any, Callable, Dict

from ..schemas import ToolCall
from ..tools import (
    research,
    shopify,
    facebook,
    whatsapp,
    content,
    supplier,
    call_fallback,
    local_actions,
)

logger = logging.getLogger("agent.executor")


TOOL_REGISTRY: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
    "research.find_winning_product": lambda args: research.find_winning_product(**args),
    "research.analyze_pricing": lambda args: research.analyze_pricing(**args),
    "shopify.draft_product": lambda args: shopify.draft_product(**args),
    "shopify.publish_product": lambda args: shopify.publish_product(**args),
    "facebook.create_post": lambda args: facebook.create_post(**args),
    "facebook.reply_comment": lambda args: facebook.reply_comment(**args),
    "facebook.reply_message": lambda args: facebook.reply_message(**args),
    "facebook.queue_posts_for_approval": lambda args: facebook.queue_posts_for_approval(**args),
    "whatsapp.send_reply": lambda args: whatsapp.send_reply(**args),
    "content.triage_inbox": lambda args: content.triage_inbox(**args),
    "content.generate_post": lambda args: content.generate_post(**args),
    "content.generate_posts_batch": lambda args: content.generate_posts_batch(**args),
    "content.generate_product_copy": lambda args: content.generate_product_copy(**args),
    "supplier.outreach_draft": lambda args: supplier.outreach_draft(**args),
    "call_fallback.missed_call_followup": lambda args: call_fallback.missed_call_followup(**args),
    "local.write_file": lambda args: local_actions.write_file(**args),
    "local.exec": lambda args: local_actions.exec_cmd(**args),
    "status.summary": lambda args: {"ok": True, "note": "Use /api/status/summary for full summary."},
}


def execute(call: ToolCall) -> Dict[str, Any]:
    """
    Executor: executes a single tool call.
    Never crashes: returns structured error on exception.
    """
    fn = TOOL_REGISTRY.get(call.name)
    if not fn:
        return {"ok": False, "error": "tool_not_found", "tool": call.name}

    try:
        out = fn(call.args or {})
        return out if isinstance(out, dict) else {"ok": True, "result": out}
    except Exception as e:
        logger.exception("tool_exec_failed", extra={"extra": {"tool": call.name, "err": str(e)}})
        return {"ok": False, "error": "exception", "tool": call.name, "message": str(e)}
