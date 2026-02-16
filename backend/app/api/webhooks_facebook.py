from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from ..deps import get_session
from ..models import AuditLog, MessageEvent
from ..settings import settings
from ..tools.content import draft_reply
from ..tools import facebook as fb

logger = logging.getLogger("webhooks.facebook")
router = APIRouter(tags=["webhooks"])


@router.get("/webhooks/facebook")
async def facebook_verify(request: Request, session: Session = Depends(get_session)):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.FACEBOOK_VERIFY_TOKEN:
        session.add(AuditLog(event_type="webhook", message="facebook_verify", payload=dict(params)))
        session.commit()
        return int(challenge or "0")

    return {"ok": False}


@router.post("/webhooks/facebook")
async def facebook_webhook(request: Request, session: Session = Depends(get_session)):
    payload = await request.json()
    session.add(AuditLog(event_type="webhook", message="facebook_event", payload=payload))
    session.commit()

    # ---------- 1) Messenger messages ----------
    try:
        for entry in (payload.get("entry") or []):
            for msg in (entry.get("messaging") or []):
                sender = (msg.get("sender") or {}).get("id") or ""
                message = msg.get("message") or {}
                text = message.get("text") or ""
                mid = message.get("mid") or ""

                # Ignore echo
                if message.get("is_echo") is True:
                    continue

                if sender and text:
                    session.add(
                        MessageEvent(
                            channel="facebook_message",
                            external_id=mid,
                            from_user=sender,
                            text=text,
                            meta={"raw": msg},
                        )
                    )
                    session.commit()

                    drafted = draft_reply(channel="facebook_message", from_user=sender, text=text, brand=None)
                    fb.reply_message(sender, drafted["text"])

    except Exception as e:
        logger.exception("facebook_message_flow_failed", extra={"extra": {"err": str(e)}})

    # ---------- 2) Feed comments ----------
    # NOTE: Feed webhooks can come in entry[].changes[].value
    try:
        for entry in (payload.get("entry") or []):
            for ch in (entry.get("changes") or []):
                value = ch.get("value") or {}

                # Typical fields for comment events:
                # item: "comment", verb: "add"
                item = value.get("item")
                verb = value.get("verb")
                if item != "comment" or verb not in ("add", "edited"):
                    continue

                comment_id = value.get("comment_id") or value.get("id") or ""
                comment_text = value.get("message") or ""
                from_id = (value.get("from") or {}).get("id") or value.get("from_id") or ""

                if comment_id and comment_text:
                    session.add(
                        MessageEvent(
                            channel="facebook_comment",
                            external_id=comment_id,
                            from_user=from_id or "unknown",
                            text=comment_text,
                            meta={"raw": ch},
                        )
                    )
                    session.commit()

                    drafted = draft_reply(channel="facebook_comment", from_user=from_id or "unknown", text=comment_text, brand=None)
                    fb.reply_comment(comment_id, drafted["text"])

    except Exception as e:
        logger.exception("facebook_comment_flow_failed", extra={"extra": {"err": str(e)}})

    return {"ok": True}
