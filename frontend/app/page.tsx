"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import StepList from "../components/StepList";
import { sendCommand } from "../lib/api";
import type { CommandResponse } from "../lib/types";

export default function ShopifyPage() {
  const [text, setText] = useState("Add a product in my store");
  const [resp, setResp] = useState<CommandResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const timerRef = useRef<any>(null);

  const autopilotStep = useMemo(() => {
    const step = resp?.steps?.find((s) => s.tool === "shopify.autopilot_add_product");
    return step?.output || null;
  }, [resp]);

  useEffect(() => {
    if (!loading) return;
    setProgress(8);
    timerRef.current = setInterval(() => {
      // Smooth fake progress while backend runs.
      setProgress((p) => {
        if (p >= 92) return p;
        const bump = p < 40 ? 6 : p < 70 ? 4 : 2;
        return Math.min(92, p + bump);
      });
    }, 450);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      timerRef.current = null;
    };
  }, [loading]);

  async function run(cmd: string) {
    setErr(null);
    setResp(null);
    setLoading(true);
    setProgress(0);
    try {
      const r = await sendCommand(cmd);
      setResp(r);
      setProgress(100);
    } catch (e: any) {
      setErr(String(e?.message || e));
      setProgress(0);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <Card
        title="Shopify Automation"
        right={
          <div className="flex items-center gap-2">
            <Badge variant={loading ? "warn" : "ok"}>{loading ? "running" : "ready"}</Badge>
            <Badge variant="neutral">one-command autopilot</Badge>
          </div>
        }
      >
        <p className="text-xs text-slate-300">
          Type one command. Recommended: <span className="text-slate-100">“Add a product in my store”</span> (this triggers full automation: research → pricing → copy → image → publish).
        </p>

        <div className="mt-3 flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder='Example: Add a product in my store niche="home" qty=50'
            className="w-full min-h-[90px] rounded-xl border border-slate-800 bg-black/30 p-3 text-sm outline-none"
          />

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => run(text)}
              disabled={!text.trim() || loading}
              className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900/40 disabled:opacity-50"
            >
              {loading ? "Running…" : "Run Command"}
            </button>
            <button
              onClick={() => setText("Add a product in my store")}
              disabled={loading}
              className="rounded-xl border border-slate-800 px-4 py-2 text-sm hover:bg-slate-900/40 disabled:opacity-50"
            >
              Use autopilot template
            </button>
            <button
              onClick={() => setText("")}
              disabled={loading}
              className="rounded-xl border border-slate-800 px-4 py-2 text-sm hover:bg-slate-900/40 disabled:opacity-50"
            >
              Clear
            </button>
          </div>

          {loading ? (
            <div className="mt-2">
              <div className="flex items-center justify-between text-[11px] text-slate-300">
                <span>Executing…</span>
                <span>{progress}%</span>
              </div>
              <div className="mt-1 h-2 w-full rounded-full border border-slate-800 bg-black/30 overflow-hidden">
                <div className="h-full bg-white/25" style={{ width: `${progress}%` }} />
              </div>
            </div>
          ) : null}

          {err ? <p className="text-xs text-rose-200 mt-2">{err}</p> : null}
        </div>
      </Card>

      {resp ? (
        <Card title={`Run #${resp.run_id}`} right={<Badge variant={resp.status === "completed" ? "ok" : "warn"}>{resp.status}</Badge>}>
          <p className="text-sm text-slate-200">{resp.summary}</p>

          {autopilotStep?.ok ? (
            <div className="mt-3 rounded-xl border border-slate-800 bg-black/20 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={autopilotStep?.simulated ? "warn" : "ok"}>
                  {autopilotStep?.simulated ? "simulated" : "published"}
                </Badge>
                <span className="text-sm text-slate-100">{autopilotStep?.title}</span>
              </div>
              <div className="mt-2 text-xs text-slate-300 space-y-1">
                <div>
                  Price: <span className="text-slate-100">${autopilotStep?.price}</span> (compare at ${autopilotStep?.compare_at})
                </div>
                {autopilotStep?.admin_url ? (
                  <div>
                    Admin:{" "}
                    <a
                      href={autopilotStep.admin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[color:var(--cyan)] underline"
                    >
                      open in Shopify
                    </a>
                  </div>
                ) : null}
                {autopilotStep?.note ? <div className="text-rose-200">{autopilotStep.note}</div> : null}
              </div>
            </div>
          ) : null}

          {autopilotStep && autopilotStep?.ok !== true ? (
            <div className="mt-3 rounded-xl border border-rose-900/60 bg-rose-950/20 p-3">
              <div className="text-sm text-rose-100">Autopilot failed</div>
              <div className="mt-1 text-xs text-rose-200 break-words">
                {autopilotStep?.error ? String(autopilotStep.error) : "Check steps below for details."}
              </div>
            </div>
          ) : null}
        </Card>
      ) : null}

      {resp?.steps ? <StepList steps={resp.steps} /> : null}
    </div>
  );
}
