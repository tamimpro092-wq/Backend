"use client";

import { useState } from "react";
import { signup } from "../lib/api";

export default function SignupPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    setLoading(true);

    const res = await signup({ username, password });

    setLoading(false);

    if (res?.detail) {
      setErr(res.detail);
      return;
    }

    window.location.href = "/login";
  }

  return (
    <div style={{ maxWidth: 420, margin: "40px auto", padding: 16 }}>
      <h1 style={{ fontSize: 24, fontWeight: 700, marginBottom: 16 }}>Sign Up</h1>

      <form onSubmit={onSubmit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span>Username</span>
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
            style={{ padding: 10, border: "1px solid #ddd", borderRadius: 8 }}
            placeholder="username"
          />
        </label>

        <label style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <span>Password</span>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            style={{ padding: 10, border: "1px solid #ddd", borderRadius: 8 }}
            placeholder="password"
          />
        </label>

        <button
          type="submit"
          disabled={loading}
          style={{
            padding: 10,
            borderRadius: 8,
            border: "1px solid #ddd",
            cursor: "pointer",
            fontWeight: 600,
          }}
        >
          {loading ? "Creating..." : "Create account"}
        </button>

        {err && <div style={{ color: "crimson" }}>{err}</div>}

        <div style={{ marginTop: 8, fontSize: 14 }}>
          Already have an account? <a href="/login">Login</a>
        </div>
      </form>
    </div>
  );
}
