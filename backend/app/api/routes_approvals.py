from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from ..deps import get_session
from ..models import Approval, AuditLog, RunRecord
from ..schemas import ApprovalDecision, CommandResponse
from ..agent.orchestrator import Orchestrator

router = APIRouter(prefix="/api", tags=["approvals"])


@router.get("/approvals")
def list_approvals(session: Session = Depends(get_session)):
    approvals = session.exec(select(Approval).order_by(Approval.id.desc())).all()
    return [
        {
            "id": a.id,
            "created_at": a.created_at.isoformat(),
            "decided_at": a.decided_at.isoformat() if a.decided_at else None,
            "run_id": a.run_id,
            "status": a.status,
            "risk_level": a.risk_level,
            "tool_name": a.tool_name,
            "tool_args": a.tool_args,
            "decision_note": a.decision_note,
        }
        for a in approvals
    ]


@router.post("/approvals/{approval_id}/decision", response_model=CommandResponse)
def decide_approval(
    approval_id: int, payload: ApprovalDecision, session: Session = Depends(get_session)
) -> CommandResponse:
    approval = session.get(Approval, approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")
    if approval.status != "pending":
        raise HTTPException(status_code=400, detail="Approval already decided")

    approval.status = "approved" if payload.decision == "approve" else "rejected"
    approval.decision_note = payload.note or ""
    approval.decided_at = datetime.now(timezone.utc)

    session.add(approval)
    session.commit()
    session.refresh(approval)

    session.add(
        AuditLog(
            run_id=approval.run_id,
            step_index=0,
            event_type="approval",
            message=f"approval_{approval.status}",
            payload={"approval_id": approval.id, "tool_name": approval.tool_name, "risk": approval.risk_level},
        )
    )
    session.commit()

    run = session.get(RunRecord, approval.run_id) if approval.run_id else None
    if not run:
        return CommandResponse(
            run_id=approval.run_id or 0,
            status="completed",
            summary=f"Approval {approval.status}. No run found to resume.",
            steps=[],
            approvals_queued=0,
        )

    orch = Orchestrator(session=session)
    return orch.resume_from_approval(run_id=run.id, approval_id=approval.id)
