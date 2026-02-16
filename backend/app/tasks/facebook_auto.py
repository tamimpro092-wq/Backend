from __future__ import annotations

from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta, timezone

from sqlmodel import Session, select

from ..db import engine
from ..models import MessageEvent, AuditLog, Approval
from ..settings import settings
from ..tools.content import draft_reply
from ..tools import facebook as facebook_tool


def _already_replied(session: Session, channel: str, external_id: str) -> bool:
    # Simple dedupe: if we logged an auto-reply for this external_id, skip
    q = select(AuditLog).where(
        AuditLog.event_type == "system",
        AuditLog.message == "facebook_auto_replied",
        AuditLog.payload["external_id"].as_string() == external_id,
    )
    row = session.exec(q).first()
    return row is not None


def facebook_autoreply_tick() -> Dict[str, Any]:
    """
    - Reads recent MessageEvent
    - Generates reply text using tools/llm.py via draft_reply()
    - Queues approval OR sends immediately (based on settings)
    """
    if not settings.FACEBOOK_AUTOREPLY_ENABLED:
        return {"ok": True, "enabled": False}

    with Session(engine) as session:
        # last 24h events (avoid infinite)
        since = datetime.now(timezone.utc) - timedelta(hours=24)

        events: List[MessageEvent] = session.exec(
            select(MessageEvent)
            .where(MessageEvent.created_at >= since)
            .order_by(MessageEvent.id.desc())
            .limit(settings.FACEBOOK_AUTOREPLY_MAX_PER_TICK)
        ).all()

        processed = 0
        queued = 0
        sent = 0
        skipped = 0
        errors = 0

        for ev in events:
            # Only react to facebook DM + comment
            if ev.channel not in ("facebook_message", "facebook_comment"):
                continue

            # Dedup
            if ev.external_id and _already_replied(session, ev.channel, ev.external_id):
                skipped += 1
                continue

            # Generate reply text
            drafted = draft_reply(channel=ev.channel, from_user=ev.from_user, text=ev.text, brand=None)
            reply_text = str(drafted.get("text") or "").strip()
            if not reply_text:
                skipped += 1
                continue

            # If approvals required: create Approval record
            if settings.FACEBOOK_AUTOREPLY_APPROVAL_REQUIRED:
                tool_name = "facebook.reply_message" if ev.channel == "facebook_message" else "facebook.reply_comment"
                tool_args = {"user_id": ev.from_user, "text": reply_text} if ev.channel == "facebook_message" else {"comment_id": ev.external_id, "text": reply_text}

                session.add(
                    Approval(
                        status="pending",
                        risk_level="high",
                        tool_name=tool_name,
                        tool_args=tool_args,
                        decision_note="auto_reply_generated",
                    )
                )
                session.add(
                    AuditLog(
                        event_type="system",
                        message="facebook_auto_reply_queued",
                        payload={"channel": ev.channel, "external_id": ev.external_id, "to": ev.from_user, "text": reply_text},
                    )
                )
                session.commit()
                queued += 1
                processed += 1
                continue

            # Otherwise send immediately
            try:
                if ev.channel == "facebook_message":
                    r = facebook_tool.reply_message(ev.from_user, reply_text)
                else:
                    r = facebook_tool.reply_comment(ev.external_id, reply_text)

                if r.get("ok"):
                    sent += 1
                    session.add(
                        AuditLog(
                            event_type="system",
                            message="facebook_auto_replied",
                            payload={"channel": ev.channel, "external_id": ev.external_id, "to": ev.from_user, "text": reply_text, "result": r},
                        )
                    )
                    session.commit()
                else:
                    errors += 1
                    session.add(
                        AuditLog(
                            event_type="system",
                            message="facebook_auto_reply_failed",
                            payload={"channel": ev.channel, "external_id": ev.external_id, "to": ev.from_user, "text": reply_text, "error": r},
                        )
                    )
                    session.commit()
            except Exception as e:
                errors += 1
                session.add(
                    AuditLog(
                        event_type="system",
                        message="facebook_auto_reply_exception",
                        payload={"err": str(e), "channel": ev.channel, "external_id": ev.external_id},
                    )
                )
                session.commit()

            processed += 1

        return {"ok": True, "enabled": True, "processed": processed, "queued": queued, "sent": sent, "skipped": skipped, "errors": errors}
