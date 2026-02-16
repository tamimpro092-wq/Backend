from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from ..deps import get_session
from ..models import AuditLog, MessageEvent
from ..settings import settings
from ..tools.content import draft_reply

logger = logging.getLogger("webhooks.whatsapp")
router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, session: Session = Depends(get_session)):
    payload = await request.json()
    session.add(AuditLog(event_type="webhook", message="whatsapp_event", payload=payload))
    session.commit()

    try:
        entries = payload.get("entry", []) or []
        for entry in entries:
            changes = entry.get("changes", []) or []
            for ch in changes:
                val = (ch.get("value") or {})
                messages = val.get("messages", []) or []
                for m in messages:
                    from_user = m.get("from", "")
                    mid = m.get("id", "")
                    body = ((m.get("text") or {}).get("body")) or ""
                    if body:
                        session.add(
                            MessageEvent(
                                channel="whatsapp_message",
                                external_id=mid,
                                from_user=from_user,
                                text=body,
                                meta={"raw": m},
                            )
                        )
        session.commit()
    except Exception as e:
        logger.exception("whatsapp_ingest_failed", extra={"extra": {"err": str(e)}})

    drafted = draft_reply(channel="whatsapp_message", from_user="unknown", text="(see logs)", brand=None)
    return {"ok": True, "draft_reply_example": drafted}


@router.get("/webhooks/whatsapp")
async def whatsapp_verify(request: Request, session: Session = Depends(get_session)):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        session.add(AuditLog(event_type="webhook", message="whatsapp_verify", payload=dict(params)))
        session.commit()
        return int(challenge or "0")

    return {"ok": False}
