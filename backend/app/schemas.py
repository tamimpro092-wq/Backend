from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class CommandRequest(BaseModel):
    text: str = Field(min_length=1)


class ToolCall(BaseModel):
    name: str
    args: Dict[str, Any] = Field(default_factory=dict)


class StepResult(BaseModel):
    index: int
    tool: str
    risk: str
    status: Literal["executed", "queued_approval", "blocked", "error"]
    output: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class CommandResponse(BaseModel):
    run_id: int
    status: str
    summary: str
    steps: List[StepResult]
    approvals_queued: int = 0


class ApprovalDecision(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = ""


class StatusResponse(BaseModel):
    ok: bool
    dry_run: bool
    brand: str
    db_path: str
    redis_url: str
    local_actions_enabled: bool
    ollama_enabled: bool


class StatusSummary(BaseModel):
    ok: bool
    dry_run: bool
    pending_approvals: int
    recent_runs: List[Dict[str, Any]]
    recent_logs: List[Dict[str, Any]]


# ✅ added (Auth schemas)
class SignupRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class UserOut(BaseModel):
    id: Optional[int] = None
    username: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
