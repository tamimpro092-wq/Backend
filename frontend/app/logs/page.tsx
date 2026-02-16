"use client";

import { useEffect, useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import { listLogs } from "../lib/api";
import type { AuditLogItem } from "../lib/types";
import { formatIso } from "../lib/util";

export default function LogsPage() {
  const [items, setItems] = useState<AuditLogItem[]>([]);
  const [limit, setLimit] = useState(100);

  async function refresh() {
    const data = await listLogs(limit);
    setItems(Array.isArray(data) ? data : []);
  }

  useEffect(() => {
    refresh();
  }, [limit]);

  return (
    <div className="space-y-4">
      <Card
        title="Audit Logs"
        right={
          <div className="flex gap-2 items-center">
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="text-xs rounded-xl border border-slate-800 bg-black/30 p-2"
            >
              <option value={50}>50</option>
              <option value={100}>100</option>
              <option value={200}>200</option>
            </select>
            <button onClick={refresh} className="text-xs rounded-full border border-slate-800 px-3 py-1 hover:bg-slate-900/40">
              Refresh
            </button>
          </div>
        }
      >
        <p className="text-xs text-slate-300">Structured JSON audit logs per run step and webhook ingestion.</p>
      </Card>

      <div className="space-y-3">
        {items.map((l) => (
          <Card
            key={l.id}
            title={`#${l.id} — ${l.event_type}:${l.message}`}
            right={<Badge variant={l.event_type === "approval" ? "warn" : l.event_type === "step" ? "neutral" : "ok"}>{l.event_type}</Badge>}
          >
            <div className="text-xs text-slate-300 space-y-1">
              <div>{formatIso(l.created_at)}</div>
              <div>Run: {l.run_id ?? "-"}</div>
              <div>Step: {l.step_index}</div>
            </div>
            <pre className="mt-3 text-xs bg-black/30 border border-slate-800 rounded-xl p-3 overflow-auto">
              {JSON.stringify(l.payload, null, 2)}
            </pre>
          </Card>
        ))}
      </div>
    </div>
  );
}
