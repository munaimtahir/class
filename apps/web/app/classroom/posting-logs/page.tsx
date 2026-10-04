"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

type PostingLog = {
  id: number;
  session: number;
  status: string;
  message: string;
  created_at: string;
};

export default function ClassroomPostingLogsPage() {
  const [logs, setLogs] = useState<PostingLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.logs().then((data) => setLogs(data || [])).finally(() => setLoading(false));
  }, []);

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Posting Logs</h1>
        <p className="text-slate-600 mt-2">Recent Classroom posting and scheduling activity.</p>
      </header>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        {loading ? (
          <p className="text-slate-500">Loading logs…</p>
        ) : logs.length === 0 ? (
          <p className="text-slate-600">No logs available yet.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {logs.map((log) => (
              <li key={log.id} className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
                <p className="font-semibold capitalize">{log.status}</p>
                <p>{log.message}</p>
                <p className="text-xs text-slate-500 mt-1">Session #{log.session} • {new Date(log.created_at).toLocaleString()}</p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}
