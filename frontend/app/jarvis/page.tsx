"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Card from "../components/Card";
import Badge from "../components/Badge";
import StepList from "../components/StepList";
import { sendCommand } from "../lib/api";
import type { CommandResponse } from "../lib/types";

declare global {
  interface Window {
    webkitSpeechRecognition?: any;
    SpeechRecognition?: any;
  }
}

export default function JarvisPage() {
  const [text, setText] = useState("");
  const [listening, setListening] = useState(false);
  const [resp, setResp] = useState<CommandResponse | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);

  const SpeechRecognition = useMemo(() => {
    if (typeof window === "undefined") return null;
    return window.SpeechRecognition || window.webkitSpeechRecognition || null;
  }, []);

  useEffect(() => {
    if (!SpeechRecognition) return;
    const rec = new SpeechRecognition();
    rec.continuous = false;
    rec.interimResults = true;
    rec.lang = "en-US";

    rec.onresult = (e: any) => {
      let transcript = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        transcript += e.results[i][0].transcript;
      }
      setText(transcript.trim());
    };

    rec.onend = () => setListening(false);
    rec.onerror = (e: any) => {
      setListening(false);
      setErr(e?.error ? String(e.error) : "Speech recognition error");
    };

    recognitionRef.current = rec;
  }, [SpeechRecognition]);

  function speak(out: string) {
    if (typeof window === "undefined") return;
    if (!("speechSynthesis" in window)) return;
    const u = new SpeechSynthesisUtterance(out);
    u.rate = 1.0;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  }

  async function run() {
    setErr(null);
    setResp(null);
    try {
      const r = await sendCommand(text);
      setResp(r);
      speak(r?.summary ? `${r.summary}` : "Done.");
    } catch (e: any) {
      setErr(String(e?.message || e));
    }
  }

  function toggleMic() {
    setErr(null);
    if (!recognitionRef.current) {
      setErr("SpeechRecognition not supported in this browser.");
      return;
    }
    if (listening) {
      recognitionRef.current.stop();
      setListening(false);
    } else {
      setListening(true);
      recognitionRef.current.start();
    }
  }

  return (
    <div className="space-y-4">
      <Card
        title="Jarvis Voice Mode"
        right={
          <div className="flex gap-2 items-center">
            <Badge variant={listening ? "ok" : "neutral"}>{listening ? "listening" : "idle"}</Badge>
            <button
              onClick={toggleMic}
              className="rounded-full border border-slate-700 px-3 py-1 text-xs hover:bg-slate-900/40"
            >
              {listening ? "Stop mic" : "Mic"}
            </button>
          </div>
        }
      >
        <p className="text-xs text-slate-300">
          Voice uses Web Speech API. If unavailable, type a command and submit.
        </p>
        <div className="mt-3 flex flex-col gap-2">
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Say or type a command..."
            className="w-full min-h-[90px] rounded-xl border border-slate-800 bg-black/30 p-3 text-sm outline-none"
          />
          <div className="flex gap-2">
            <button
              onClick={run}
              disabled={!text.trim()}
              className="rounded-xl border border-slate-700 px-4 py-2 text-sm hover:bg-slate-900/40 disabled:opacity-50"
            >
              Run
            </button>
            <button
              onClick={() => setText("")}
              className="rounded-xl border border-slate-800 px-4 py-2 text-sm hover:bg-slate-900/40"
            >
              Clear
            </button>
          </div>
          {err ? <p className="text-xs text-rose-200">{err}</p> : null}
        </div>
      </Card>

      {resp ? (
        <Card
          title={`Run #${resp.run_id}`}
          right={
            <div className="flex gap-2">
              <Badge variant={resp.status === "completed" ? "ok" : "warn"}>{resp.status}</Badge>
              {resp.approvals_queued ? <Badge variant="warn">{resp.approvals_queued} approvals</Badge> : <Badge variant="ok">no approvals</Badge>}
            </div>
          }
        >
          <p className="text-sm text-slate-200">{resp.summary}</p>
        </Card>
      ) : null}

      {resp?.steps ? <StepList steps={resp.steps} /> : null}
    </div>
  );
}
