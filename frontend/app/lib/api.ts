import { BackendStatus, CommandResponse, ApprovalItem, AuditLogItem, StatusSummary } from "./types";

const internalBase = process.env.BACKEND_INTERNAL_URL || "http://backend:8000";
const browserBase = process.env.NEXT_PUBLIC_BACKEND_BROWSER_URL || "http://localhost:8000";

async function safeJson(res: Response) {
  const text = await res.text();
  try {
    return JSON.parse(text);
  } catch {
    return { ok: false, raw: text };
  }
}

export async function fetchStatus(): Promise<BackendStatus> {
  const res = await fetch(`${internalBase}/api/status`, { cache: "no-store" });
  return safeJson(res);
}

export async function fetchSummary(): Promise<StatusSummary> {
  const res = await fetch(`${internalBase}/api/status/summary`, { cache: "no-store" });
  return safeJson(res);
}

export async function sendCommand(text: string): Promise<CommandResponse> {
  const res = await fetch(`${browserBase}/api/command`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text })
  });
  return safeJson(res);
}

export async function listApprovals(): Promise<ApprovalItem[]> {
  const res = await fetch(`${browserBase}/api/approvals`, { cache: "no-store" });
  return safeJson(res);
}

export async function decideApproval(id: number, decision: "approve" | "reject", note: string): Promise<CommandResponse> {
  const res = await fetch(`${browserBase}/api/approvals/${id}/decision`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ decision, note })
  });
  return safeJson(res);
}

export async function listLogs(limit = 100, runId?: number): Promise<AuditLogItem[]> {
  const url = new URL(`${browserBase}/api/logs`);
  url.searchParams.set("limit", String(limit));
  if (runId) url.searchParams.set("run_id", String(runId));
  const res = await fetch(url.toString(), { cache: "no-store" });
  return safeJson(res);
}
