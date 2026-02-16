"use client";

import { useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import StepList from "../components/StepList";
import { sendCommand } from "../lib/api";
import type { CommandResponse } from "../lib/types";

export default function WhatsAppPage() {
  const [to, setTo] = useState("8801555123456");
  const [text, setText] = useState("Hello! Please share your order number so we can help.");
  const [resp, setResp] = useState<CommandResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run(cmd: string) {
    setErr(null);
    setResp(null);
    try {
      const r = await sendCommand(cmd);
      setResp(r);
    } catch (e: any) {
      setErr(String(e?.message || e));
    }
  }

  return (
    <div className="space-y-4">
      <Card title="WhatsApp Automation" right={<Badge variant="warn">send requires approval</Badge>}>
        <div className="rounded-xl border border-slate-800 p-3 bg-black/20">
          <div className="text-xs text-slate-300 mb-2">Reply on WhatsApp</div>
          <div className="flex gap-2">
            <input
              value={to}
              onChange={(e) => setTo(e.target.value)}
              className="w-48 rounded-xl border border-slate-800 bg-black/30 p-2 text-sm outline-none"
            />
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              className="flex-1 rounded-xl border border-slate-800 bg-black/30 p-2 text-sm outline-none"
            />
          </div>
          <button
            onClick={() => run(`Reply on WhatsApp to ${to} with ${text}`)}
            className="mt-2 rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900/40"
          >
            Queue approval
          </button>
        </div>
        {err ? <p className="text-xs text-rose-200 mt-2">{err}</p> : null}
      </Card>

      {resp ? (
        <Card title={`Run #${resp.run_id}`} right={<Badge variant={resp.status === "completed" ? "ok" : "warn"}>{resp.status}</Badge>}>
          <p className="text-sm text-slate-200">{resp.summary}</p>
        </Card>
      ) : null}

      {resp?.steps ? <StepList steps={resp.steps} /> : null}
    </div>
  );
}
