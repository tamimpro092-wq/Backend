from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from ..deps import get_session
from ..schemas import CommandRequest, CommandResponse
from ..agent.orchestrator import Orchestrator

router = APIRouter(prefix="/api", tags=["command"])


@router.post("/command", response_model=CommandResponse)
def post_command(payload: CommandRequest, session: Session = Depends(get_session)) -> CommandResponse:
    orch = Orchestrator(session=session)
    return orch.handle_command(payload.text)
