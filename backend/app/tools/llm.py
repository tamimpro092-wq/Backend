from __future__ import annotations

import logging
import re
from typing import Any, Dict

import httpx

from ..settings import settings

logger = logging.getLogger("tools.llm")


# ------------------------------
# Prompts
# ------------------------------
def system_prompt(brand: str, channel: str) -> str:
    # Channel helps tone
    where = "public comment" if "comment" in (channel or "") else "private message"
    return (
        "You are a customer support assistant for an e-commerce brand.\n"
        f"You are replying in a {where}.\n\n"
        "Hard rules:\n"
        f'- The reply MUST include exactly once the phrase: "I\'m the AI assistant for {brand}".\n'
        "- Never hallucinate order status.\n"
        "- If the message is about order/shipping/delivery: ask for order number + email/phone used at checkout.\n"
        "- If the message is about refund/return: ask for order number and say a human will review.\n"
        "- Never promise refunds.\n"
        "- Keep it human-like and concise.\n"
        "- Ask at most ONE question per reply.\n"
        "- Do not mention policies, tools, tokens, webhooks, or internal systems.\n"
    )


def _base_prefix(brand: str) -> str:
    # The exact required phrase once
    return f"I'm the AI assistant for {brand}. "


# ------------------------------
# Helpers (enforce the exact phrase once)
# ------------------------------
_REQUIRED_RE = re.compile(r"I'm the AI assistant for ([^.\n]+)\.", re.IGNORECASE)


def _strip_required_phrase(text: str) -> str:
    # remove any occurrences, we will add exactly once ourselves
    return _REQUIRED_RE.sub("", text).strip()


def _finalize(brand: str, text: str) -> str:
    # Clean, ensure single phrase, ensure not empty
    cleaned = _strip_required_phrase(text)

    # Remove double spaces after stripping
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        cleaned = "Thanks for reaching out—how can I help?"

    # Add the required phrase exactly once at the start
    out = _base_prefix(brand) + cleaned

    # Final cleanup
    out = re.sub(r"\s+", " ", out).strip()

    # Safety: enforce EXACTLY once
    out = _strip_required_phrase(out)
    out = _base_prefix(brand) + out

    return out.strip()


# ------------------------------
# Deterministic fallback (human style)
# ------------------------------
def _deterministic_reply(brand: str, user_text: str, channel: str) -> str:
    t = (user_text or "").lower().strip()

    is_public = "comment" in (channel or "")
    short_end = "" if is_public else " (so I can look it up)."

    if any(k in t for k in ["order", "shipping", "delivery", "delivered", "where", "track", "tracking"]):
        return _finalize(
            brand,
            "Sure—please share your order number and the email/phone used at checkout" + short_end,
        )

    if any(k in t for k in ["refund", "return", "money back", "cancel"]):
        return _finalize(
            brand,
            "I can help with next steps—please share your order number and a human will review your request.",
        )

    # generic
    if is_public:
        return _finalize(brand, "Thanks for the comment—what do you need help with?")
    return _finalize(brand, "Thanks for reaching out—what can I help you with today?")


# ------------------------------
# Main generator
# ------------------------------
def generate(brand: str, user_text: str, channel: str = "generic") -> Dict[str, Any]:
    # 1) Ollama
    if bool(settings.OLLAMA_ENABLED):
        try:
            url = f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate"
            payload = {
                "model": settings.OLLAMA_MODEL,
                "prompt": f"{system_prompt(brand, channel)}\nUser: {user_text}\nAssistant:",
                "stream": False,
            }
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, json=payload)
                if r.status_code < 400:
                    data = r.json()
                    text = str(data.get("response", "")).strip()
                    if not text:
                        return {"ok": True, "provider": "ollama", "text": _deterministic_reply(brand, user_text, channel)}
                    return {"ok": True, "provider": "ollama", "text": _finalize(brand, text)}
                logger.warning("ollama_failed", extra={"extra": {"status": r.status_code, "body": r.text}})
        except Exception as e:
            logger.warning("ollama_exception", extra={"extra": {"err": str(e)}})

    # 2) OpenAI
    if settings.OPENAI_API_KEY:
        try:
            url = f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions"
            headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}", "Content-Type": "application/json"}
            payload = {
                "model": settings.OPENAI_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt(brand, channel)},
                    {"role": "user", "content": user_text},
                ],
                "temperature": 0.2,
            }
            with httpx.Client(timeout=30.0) as client:
                r = client.post(url, headers=headers, json=payload)
                if r.status_code < 400:
                    data = r.json()
                    text = (((data.get("choices") or [{}])[0].get("message") or {}).get("content")) or ""
                    text = text.strip()
                    if not text:
                        return {"ok": True, "provider": "openai", "text": _deterministic_reply(brand, user_text, channel)}
                    return {"ok": True, "provider": "openai", "text": _finalize(brand, text)}
                logger.warning("openai_failed", extra={"extra": {"status": r.status_code, "body": r.text}})
        except Exception as e:
            logger.warning("openai_exception", extra={"extra": {"err": str(e)}})

    # 3) fallback
    return {"ok": True, "provider": "deterministic", "text": _deterministic_reply(brand, user_text, channel)}
