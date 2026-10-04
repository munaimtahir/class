"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "../../../lib/api";

type AuthStatus = {
  authenticated: boolean;
  user?: { name: string; email: string };
  granted_scopes?: string[];
  google_last_refresh_at?: string | null;
};

export default function AdministrationWorkspaceConnectionPage() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const load = async () => {
    const auth = await api.authStatus();
    setStatus(auth);
  };

  useEffect(() => {
    load().catch(() => setStatus({ authenticated: false }));
  }, []);

  const reconnect = async (mode: "reconnect" | "upgrade" = "reconnect") => {
    setBusy(true);
    setMsg("");
    try {
      const start = await api.authStart({ mode });
      window.location.href = start.auth_url;
    } catch (error: unknown) {
      setMsg(error instanceof Error ? error.message : "Failed to start reconnect flow.");
      setBusy(false);
    }
  };

  const groupedScopes = useMemo(() => {
    const scopes = status?.granted_scopes || [];
    return scopes.sort((a, b) => a.localeCompare(b));
  }, [status?.granted_scopes]);

  return (
    <div className="max-w-5xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Workspace Connection</h1>
        <p className="text-slate-600 mt-2">
          Manage Google OAuth connection health and permission upgrades for operational actions.
        </p>
      </header>

      {msg ? (
        <div className="rounded-lg border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {msg}
        </div>
      ) : null}

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <p className="text-sm text-slate-500">Connection</p>
        <p className="text-lg font-semibold mt-1">
          {status?.authenticated ? "Connected" : "Not Connected"}
        </p>
        {status?.user ? (
          <p className="text-sm text-slate-600 mt-2">
            {status.user.name} ({status.user.email})
          </p>
        ) : null}
        <p className="text-xs text-slate-500 mt-2">
          Last token refresh:{" "}
          {status?.google_last_refresh_at
            ? new Date(status.google_last_refresh_at).toLocaleString()
            : "Not available"}
        </p>
        <div className="mt-3 flex gap-2">
          <button
            onClick={() => reconnect("reconnect")}
            disabled={busy}
            className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
          >
            {busy ? "Starting reconnect…" : "Reconnect Google"}
          </button>
          <button
            onClick={() => reconnect("upgrade")}
            disabled={busy}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50 disabled:opacity-60"
          >
            Upgrade Permissions
          </button>
        </div>
      </section>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h2 className="text-lg font-semibold text-slate-900">Granted Scopes</h2>
        {groupedScopes.length === 0 ? (
          <p className="text-sm text-slate-500 mt-2">No scopes recorded yet.</p>
        ) : (
          <ul className="mt-3 space-y-2 text-xs">
            {groupedScopes.map((scope) => (
              <li key={scope} className="rounded border border-slate-200 bg-slate-50 px-3 py-2 break-all">
                {scope}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
