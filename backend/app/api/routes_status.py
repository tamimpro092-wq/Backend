from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from ..deps import get_session
from ..settings import settings
from ..models import Approval, RunRecord, AuditLog
from ..schemas import StatusResponse, StatusSummary

router = APIRouter(prefix="/api", tags=["status"])


@router.get("/status", response_model=StatusResponse)
def get_status() -> StatusResponse:
    return StatusResponse(
        ok=True,
        dry_run=bool(settings.DRY_RUN),
        brand=settings.BRAND_NAME,
        db_path=settings.DATABASE_PATH,
        redis_url=settings.REDIS_URL,
        local_actions_enabled=bool(settings.LOCAL_ACTIONS_ENABLED),
        ollama_enabled=bool(settings.OLLAMA_ENABLED),
    )


@router.get("/status/summary", response_model=StatusSummary)
def get_status_summary(session: Session = Depends(get_session)) -> StatusSummary:
    pending = session.exec(select(Approval).where(Approval.status == "pending")).all()
    runs = session.exec(select(RunRecord).order_by(RunRecord.id.desc()).limit(10)).all()
    logs = session.exec(select(AuditLog).order_by(AuditLog.id.desc()).limit(20)).all()

    return StatusSummary(
        ok=True,
        dry_run=bool(settings.DRY_RUN),
        pending_approvals=len(pending),
        recent_runs=[
            {"id": r.id, "created_at": r.created_at.isoformat(), "status": r.status, "summary": r.summary}
            for r in runs
        ],
        recent_logs=[
            {
                "id": l.id,
                "created_at": l.created_at.isoformat(),
                "run_id": l.run_id,
                "event_type": l.event_type,
                "message": l.message,
            }
            for l in logs
        ],
    )
