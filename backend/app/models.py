from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlmodel import SQLModel, Field, Column, JSON


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    run_id: Optional[int] = Field(default=None, index=True)
    step_index: int = Field(default=0)
    event_type: str = Field(default="step")  # step, approval, webhook, system
    message: str = Field(default="")
    payload: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class RunRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    command_text: str = Field(default="")
    status: str = Field(default="created")  # created, completed, failed, queued_approval
    summary: str = Field(default="")
    result_json: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class Approval(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    decided_at: Optional[datetime] = Field(default=None, index=True)
    run_id: Optional[int] = Field(default=None, index=True)

    status: str = Field(default="pending")  # pending, approved, rejected
    risk_level: str = Field(default="high")  # low, medium, high
    tool_name: str = Field(default="")
    tool_args: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
    decision_note: str = Field(default="")


class ProductDraft(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    title: str = Field(default="")
    description: str = Field(default="")
    price: float = Field(default=0.0)
    currency: str = Field(default="USD")
    status: str = Field(default="draft")  # draft, published, simulated_published
    external_id: str = Field(default="")
    meta: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class MessageEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    channel: str = Field(default="unknown")  # facebook_comment, facebook_message, whatsapp_message
    external_id: str = Field(default="")
    from_user: str = Field(default="")
    text: str = Field(default="")
    processed: bool = Field(default=False, index=True)  # ✅ NEW (prevents duplicate auto-replies)
    meta: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))




class BrandVoiceProfile(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=utcnow, index=True)
    brand_name: str = Field(default="Acme")
    tone: str = Field(default="concise, friendly, helpful")
    do_say: str = Field(default="I'm the AI assistant for {brand}")
    must_not: str = Field(
        default="Never hallucinate order status. Ask for order number. Never promise refunds. No voice-call auto answering."
    )
    extra: Dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))
