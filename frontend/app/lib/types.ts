export type BackendStatus = {
  ok: boolean;
  dry_run: boolean;
  brand: string;
  db_path: string;
  redis_url: string;
  local_actions_enabled: boolean;
  ollama_enabled: boolean;
};

export type StepResult = {
  index: number;
  tool: string;
  risk: string;
  status: "executed" | "queued_approval" | "blocked" | "error";
  output: any;
  error?: string | null;
};

export type CommandResponse = {
  run_id: number;
  status: string;
  summary: string;
  steps: StepResult[];
  approvals_queued: number;
};

export type ApprovalItem = {
  id: number;
  created_at: string;
  decided_at: string | null;
  run_id: number | null;
  status: string;
  risk_level: string;
  tool_name: string;
  tool_args: any;
  decision_note: string;
};

export type AuditLogItem = {
  id: number;
  created_at: string;
  run_id: number | null;
  step_index: number;
  event_type: string;
  message: string;
  payload: any;
};

export type StatusSummary = {
  ok: boolean;
  dry_run: boolean;
  pending_approvals: number;
  recent_runs: any[];
  recent_logs: any[];
};

// ✅ added (Auth types)
export type SignupRequest = {
  username: string;
  password: string;
};

export type LoginRequest = {
  username: string;
  password: string;
};

export type UserOut = {
  id?: number | null;
  username: string;
};

export type LoginResponse = {
  access_token: string;
  token_type: string;
  user: UserOut;
};
