from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from ..deps import get_session
from ..models import AuditLog

router = APIRouter(prefix="/api", tags=["logs"])


@router.get("/logs")
def list_logs(
    session: Session = Depends(get_session),
    limit: int = Query(50, ge=1, le=500),
    run_id: int | None = Query(None),
):
    stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit)
    if run_id is not None:
        stmt = select(AuditLog).where(AuditLog.run_id == run_id).order_by(AuditLog.id.desc()).limit(limit)

    logs = session.exec(stmt).all()
    return [
        {
            "id": l.id,
            "created_at": l.created_at.isoformat(),
            "run_id": l.run_id,
            "step_index": l.step_index,
            "event_type": l.event_type,
            "message": l.message,
            "payload": l.payload,
        }
        for l in logs
    ]
