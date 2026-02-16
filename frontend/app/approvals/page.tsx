"use client";

import { useEffect, useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import { decideApproval, listApprovals } from "../lib/api";
import type { ApprovalItem, CommandResponse } from "../lib/types";
import { formatIso } from "../lib/util";

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalItem[]>([]);
  const [busy, setBusy] = useState<number | null>(null);
  const [note, setNote] = useState<Record<number, string>>({});
  const [lastRun, setLastRun] = useState<CommandResponse | null>(null);

  async function refresh() {
    const data = await listApprovals();
    setItems(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    refresh();
  }, []);

  async function act(id: number, decision: "approve" | "reject") {
    setBusy(id);
    try {
      const r = await decideApproval(id, decision, note[id] || "");
      setLastRun(r);
      await refresh();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      <Card
        title="Approvals Queue"
        right={
          <button onClick={refresh} className="text-xs rounded-full border border-slate-800 px-3 py-1 hover:bg-slate-900/40">
            Refresh
          </button>
        }
      >
        <p className="text-xs text-slate-300">
          High-risk actions are queued here. Approving executes the queued tool call with policy enforcement.
        </p>
      </Card>

      {lastRun ? (
        <Card
          title={`Last execution (Run #${lastRun.run_id})`}
          right={<Badge variant={lastRun.status === "completed" ? "ok" : "warn"}>{lastRun.status}</Badge>}
        >
          <p className="text-sm text-slate-200">{lastRun.summary}</p>
        </Card>
      ) : null}

      <div className="space-y-3">
        {items.map((a) => (
          <Card
            key={a.id}
            title={`Approval #${a.id} — ${a.tool_name}`}
            right={
              <div className="flex gap-2 items-center">
                <Badge variant={a.risk_level === "high" ? "danger" : a.risk_level === "medium" ? "warn" : "ok"}>{a.risk_level}</Badge>
                <Badge variant={a.status === "pending" ? "warn" : a.status === "approved" ? "ok" : "danger"}>{a.status}</Badge>
              </div>
            }
          >
            <div className="text-xs text-slate-300 space-y-1">
              <div>Created: {formatIso(a.created_at)}</div>
              {a.decided_at ? <div>Decided: {formatIso(a.decided_at)}</div> : null}
              <div>Run ID: {a.run_id ?? "-"}</div>
            </div>

            <pre className="mt-3 text-xs bg-black/30 border border-slate-800 rounded-xl p-3 overflow-auto">
              {JSON.stringify(a.tool_args, null, 2)}
            </pre>

            {a.status === "pending" ? (
              <div className="mt-3 flex flex-col gap-2">
                <input
                  value={note[a.id] || ""}
                  onChange={(e) => setNote((p) => ({ ...p, [a.id]: e.target.value }))}
                  placeholder="Decision note (optional)"
                  className="w-full rounded-xl border border-slate-800 bg-black/30 p-2 text-sm outline-none"
                />
                <div className="flex gap-2">
                  <button
                    onClick={() => act(a.id, "approve")}
                    disabled={busy === a.id}
                    className="rounded-xl border border-emerald-700 px-4 py-2 text-sm hover:bg-emerald-900/20 disabled:opacity-50"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => act(a.id, "reject")}
                    disabled={busy === a.id}
                    className="rounded-xl border border-rose-700 px-4 py-2 text-sm hover:bg-rose-900/20 disabled:opacity-50"
                  >
                    Reject
                  </button>
                </div>
              </div>
            ) : (
              <p className="mt-3 text-xs text-slate-300">Decision note: {a.decision_note || "-"}</p>
            )}
          </Card>
        ))}
      </div>
    </div>
  );
}
