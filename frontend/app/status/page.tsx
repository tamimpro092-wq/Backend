import Card from "../components/Card";
import Badge from "../components/Badge";
import { fetchStatus, fetchSummary } from "../lib/api";

export default async function StatusPage() {
  const status = await fetchStatus();
  const summary = await fetchSummary();

  const dry = Boolean(status?.dry_run);

  return (
    <div className="space-y-4">
      <Card
        title="System Status"
        right={
          <div className="flex gap-2">
            <Badge variant={dry ? "warn" : "ok"}>{dry ? "DRY_RUN=1" : "DRY_RUN=0"}</Badge>
            <Badge variant={status?.ok ? "ok" : "danger"}>{status?.ok ? "ok" : "down"}</Badge>
          </div>
        }
      >
        <pre className="text-xs bg-black/30 border border-slate-800 rounded-xl p-3 overflow-auto">
          {JSON.stringify(status, null, 2)}
        </pre>
      </Card>

      <Card
        title="Summary"
        right={<Badge variant={summary?.pending_approvals ? "warn" : "ok"}>{summary?.pending_approvals || 0} pending</Badge>}
      >
        <pre className="text-xs bg-black/30 border border-slate-800 rounded-xl p-3 overflow-auto">
          {JSON.stringify(summary, null, 2)}
        </pre>
      </Card>
    </div>
  );
}
