import Card from "./Card";
import Badge from "./Badge";
import { StepResult } from "../lib/types";

export default function StepList({ steps }: { steps: StepResult[] }) {
  if (!steps?.length) return null;

  return (
    <div className="space-y-3">
      {steps.map((s) => (
        <Card
          key={`${s.index}-${s.tool}`}
          title={`Step ${s.index}: ${s.tool}`}
          right={
            <div className="flex gap-2">
              <Badge variant={s.risk === "high" ? "danger" : s.risk === "medium" ? "warn" : "ok"}>{s.risk}</Badge>
              <Badge variant={s.status === "executed" ? "ok" : s.status === "queued_approval" ? "warn" : "danger"}>
                {s.status}
              </Badge>
            </div>
          }
        >
          <pre className="text-xs bg-black/30 border border-slate-800 rounded-xl p-3 overflow-auto">
            {JSON.stringify(s.output, null, 2)}
          </pre>
          {s.error ? <p className="text-xs text-rose-200 mt-2">{s.error}</p> : null}
        </Card>
      ))}
    </div>
  );
}
