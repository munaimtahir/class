"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

type SyncJob = {
  id: number;
  status: string;
  started_at: string;
  completed_at: string | null;
  pages_fetched: number;
  users_fetched_total: number;
  users_upserted_total: number;
};

export default function DirectorySyncHistoryPage() {
  const [jobs, setJobs] = useState<SyncJob[]>([]);
  const [loading, setLoading] = useState(true);
  const [runningSync, setRunningSync] = useState(false);

  const load = async () => {
    setLoading(true);
    const data = await api.listDirectorySyncJobs();
    setJobs(data || []);
    setLoading(false);
  };

  useEffect(() => {
    load().catch(() => setLoading(false));
  }, []);

  const triggerSync = async () => {
    setRunningSync(true);
    try {
      await api.syncDirectory({});
      await load();
    } finally {
      setRunningSync(false);
    }
  };

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200 flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Sync History</h1>
          <p className="text-slate-600 mt-2">Directory sync timeline with authoritative cumulative counts.</p>
        </div>
        <button
          onClick={triggerSync}
          disabled={runningSync}
          className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60"
        >
          {runningSync ? "Syncing…" : "Run Sync"}
        </button>
      </header>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        {loading ? (
          <p className="text-slate-500">Loading sync jobs…</p>
        ) : jobs.length === 0 ? (
          <p className="text-slate-600">No sync jobs found yet.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left p-2">Job</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Fetched</th>
                <th className="text-left p-2">Upserted</th>
                <th className="text-left p-2">Pages</th>
                <th className="text-left p-2">Completed</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map((job) => (
                <tr key={job.id} className="border-b">
                  <td className="p-2">#{job.id}</td>
                  <td className="p-2 capitalize">{job.status}</td>
                  <td className="p-2">{job.users_fetched_total}</td>
                  <td className="p-2">{job.users_upserted_total}</td>
                  <td className="p-2">{job.pages_fetched}</td>
                  <td className="p-2">{job.completed_at ? new Date(job.completed_at).toLocaleString() : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
