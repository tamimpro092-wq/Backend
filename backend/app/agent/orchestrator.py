from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlmodel import Session

from ..models import RunRecord, AuditLog
from ..schemas import CommandResponse, StepResult
from . import planner
from .policy import evaluate
from .executor import execute

logger = logging.getLogger("agent.orchestrator")


class Orchestrator:
    """
    Approvals REMOVED:
    - Any policy decision 'needs_approval' is treated as 'allowed'
    - No Approval rows are created
    - No queued_approval status exists
    """

    def __init__(self, session: Session):
        self.session = session

    def _log(
        self,
        run_id: Optional[int],
        step_index: int,
        event_type: str,
        message: str,
        payload: Dict[str, Any],
    ) -> None:
        self.session.add(
            AuditLog(
                run_id=run_id,
                step_index=step_index,
                event_type=event_type,
                message=message,
                payload=payload,
            )
        )
        self.session.commit()

    def handle_command(self, text: str) -> CommandResponse:
        run = RunRecord(command_text=text, status="created", summary="", result_json={})
        self.session.add(run)
        self.session.commit()
        self.session.refresh(run)

        calls = planner.plan(text)
        self._log(
            run.id,
            0,
            "system",
            "planned",
            {"command": text, "calls": [c.model_dump() for c in calls]},
        )

        steps: List[StepResult] = []

        for idx, call in enumerate(calls, start=1):
            pol = evaluate(call, context={"run_id": run.id})

            # approvals disabled => convert needs_approval -> allowed
            pol_dict = pol.__dict__.copy()
            if pol_dict.get("action") == "needs_approval":
                pol_dict["action"] = "allowed"
                pol_dict["risk"] = pol_dict.get("risk") or "high"
                pol_dict["reason"] = (pol_dict.get("reason") or "") + " | approvals_disabled: executed immediately"

            self._log(
                run.id,
                idx,
                "step",
                "policy",
                {"tool": call.name, "decision": pol_dict, "args": call.args},
            )

            if pol.action == "blocked":
                steps.append(
                    StepResult(
                        index=idx,
                        tool=call.name,
                        risk=pol.risk,
                        status="blocked",
                        output={"reason": pol.reason},
                    )
                )
                continue

            # execute immediately (allowed OR needs_approval treated as allowed)
            out = execute(call)

            if out.get("ok") is True:
                steps.append(
                    StepResult(
                        index=idx,
                        tool=call.name,
                        risk=pol.risk,
                        status="executed",
                        output=out,
                    )
                )
                self._log(run.id, idx, "step", "executed", {"tool": call.name, "output": out})
            else:
                steps.append(
                    StepResult(
                        index=idx,
                        tool=call.name,
                        risk=pol.risk,
                        status="error",
                        output=out,
                        error=out.get("message"),
                    )
                )
                self._log(run.id, idx, "step", "error", {"tool": call.name, "output": out})

        # No queued approval concept anymore
        run.status = "completed"
        run.summary = "Completed."
        run.result_json = {
            "steps": [s.model_dump() for s in steps],
            "approvals_queued": 0,
            "approvals_disabled": True,
        }

        self.session.add(run)
        self.session.commit()

        return CommandResponse(
            run_id=run.id,
            status=run.status,
            summary=run.summary,
            steps=steps,
            approvals_queued=0,
        )

    def resume_from_approval(self, run_id: int, approval_id: int) -> CommandResponse:
        # Approvals are removed, so this endpoint shouldn't be used anymore.
        return CommandResponse(
            run_id=run_id,
            status="failed",
            summary="Approvals are disabled; nothing to resume.",
            steps=[],
            approvals_queued=0,
        )
