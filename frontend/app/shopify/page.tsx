"use client";

import { useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import StepList from "../components/StepList";
import { sendCommand } from "../lib/api";
import type { CommandResponse } from "../lib/types";

export default function ShopifyPage() {
  const [resp, setResp] = useState<CommandResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  async function run(text: string) {
    setErr(null);
    setResp(null);
    try {
      const r = await sendCommand(text);
      setResp(r);
    } catch (e: any) {
      setErr(String(e?.message || e));
    }
  }

  return (
    <div className="space-y-4">
      <Card title="Shopify Automation" right={<Badge variant="warn">publish requires approval</Badge>}>
        <div className="flex flex-wrap gap-2">
          <button
            onClick={() => run("Add a winning product and prepare it to sell")}
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900/40"
          >
            Research → Draft → Copy
          </button>
          <button
            onClick={() => run("Analyze product and propose best price")}
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900/40"
          >
            Analyze Pricing
          </button>
          <button
            onClick={() => run("Publish product 1")}
            className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900/40"
          >
            Publish Draft #1
          </button>
        </div>
        <p className="text-xs text-slate-300 mt-3">
          Publishing always queues approval (and simulates if DRY_RUN=1 or missing creds).
        </p>
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
