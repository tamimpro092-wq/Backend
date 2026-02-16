from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx
from ..settings import settings

logger = logging.getLogger("tools.facebook")

_POST_BUFFER: List[Dict[str, Any]] = []


def _graph_url(path: str) -> str:
    v = (settings.FACEBOOK_GRAPH_VERSION or "v19.0").strip()
    if not path.startswith("/"):
        path = "/" + path
    return f"https://graph.facebook.com/{v}{path}"


def _require_token() -> None:
    if not settings.FACEBOOK_ACCESS_TOKEN:
        raise RuntimeError("FACEBOOK_ACCESS_TOKEN is missing")
    if not settings.FACEBOOK_PAGE_ID:
        raise RuntimeError("FACEBOOK_PAGE_ID is missing")


def create_post(text_from: str = "generated", text: str | None = None) -> Dict[str, Any]:
    post_text = text or f"New drop! ({text_from}) Reply with your order number if you need help."

    if bool(settings.DRY_RUN):
        return {"ok": True, "simulated": True, "page_id": settings.FACEBOOK_PAGE_ID or "dry_run_page", "text": post_text}

    try:
        _require_token()
        url = _graph_url(f"/{settings.FACEBOOK_PAGE_ID}/feed")
        payload = {"message": post_text, "access_token": settings.FACEBOOK_ACCESS_TOKEN}
        with httpx.Client(timeout=20.0) as client:
            r = client.post(url, data=payload)
        if r.status_code >= 400:
            logger.error("facebook_create_post_failed", extra={"extra": {"status": r.status_code, "body": r.text}})
            return {"ok": False, "error": "facebook_error", "status_code": r.status_code, "body": r.text}
        return {"ok": True, "simulated": False, "result": r.json(), "text": post_text}
    except Exception as e:
        logger.exception("facebook_post_exception", extra={"extra": {"err": str(e)}})
        return {"ok": False, "error": "exception", "message": str(e)}


def reply_comment(comment_id: str, text: str) -> Dict[str, Any]:
    if bool(settings.DRY_RUN):
        return {"ok": True, "simulated": True, "comment_id": comment_id, "text": text}

    try:
        _require_token()
        url = _graph_url(f"/{comment_id}/comments")
        payload = {"message": text, "access_token": settings.FACEBOOK_ACCESS_TOKEN}
        with httpx.Client(timeout=20.0) as client:
            r = client.post(url, data=payload)
        if r.status_code >= 400:
            logger.error("facebook_reply_comment_failed", extra={"extra": {"status": r.status_code, "body": r.text}})
            return {"ok": False, "error": "facebook_error", "status_code": r.status_code, "body": r.text}
        return {"ok": True, "simulated": False, "result": r.json(), "comment_id": comment_id}
    except Exception as e:
        logger.exception("facebook_reply_comment_exception", extra={"extra": {"err": str(e)}})
        return {"ok": False, "error": "exception", "message": str(e)}


def reply_message(psid: str, text: str) -> Dict[str, Any]:
    """
    Messenger send API (Page Inbox auto-reply)
    Requires:
      - a Page access token
      - permissions: pages_messaging
    """
    if bool(settings.DRY_RUN):
        return {"ok": True, "simulated": True, "psid": psid, "text": text}

    try:
        _require_token()
        url = _graph_url("/me/messages")
        payload = {
            "recipient": {"id": psid},
            "message": {"text": text},
            "messaging_type": "RESPONSE",
            "access_token": settings.FACEBOOK_ACCESS_TOKEN,
        }
        with httpx.Client(timeout=20.0) as client:
            r = client.post(url, json=payload)

        if r.status_code >= 400:
            logger.error("facebook_reply_message_failed", extra={"extra": {"status": r.status_code, "body": r.text}})
            return {"ok": False, "error": "facebook_error", "status_code": r.status_code, "body": r.text}

        return {"ok": True, "simulated": False, "result": r.json(), "psid": psid}
    except Exception as e:
        logger.exception("facebook_reply_message_exception", extra={"extra": {"err": str(e)}})
        return {"ok": False, "error": "exception", "message": str(e)}


def queue_posts_for_approval(count: int = 7) -> Dict[str, Any]:
    queued = []
    for i in range(count):
        item = {"idx": i + 1, "text": f"Post #{i+1}"}
        queued.append(item)
        _POST_BUFFER.append(item)
    return {"ok": True, "queued": queued, "buffer_size": len(_POST_BUFFER)}
