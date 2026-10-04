"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

type DirectoryStats = {
  total_directory_users: number;
  latest_sync_job: { completed_at: string | null } | null;
  running_sync_job: { users_fetched_total: number; pages_fetched: number } | null;
};

export default function AdministrationSyncControlsPage() {
  const [stats, setStats] = useState<DirectoryStats | null>(null);
  const [busy, setBusy] = useState<string>("");
  const [message, setMessage] = useState("");

  const load = async () => {
    const data = await api.directoryStats();
    setStats(data || null);
  };

  useEffect(() => {
    load().catch(() => undefined);
  }, []);

  const runClassroomSync = async () => {
    setBusy("classroom");
    setMessage("");
    try {
      const result = await api.syncCourses();
      setMessage(`Classroom sync completed: ${result.synced ?? 0} course(s).`);
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : "Classroom sync failed.");
    } finally {
      setBusy("");
    }
  };

  const runDirectorySync = async () => {
    setBusy("directory");
    setMessage("");
    try {
      const result = await api.syncDirectory({});
      setMessage(`Directory sync completed: ${result.synced ?? 0} user(s) across ${result.pages_fetched ?? 0} page(s).`);
      await load();
    } catch (error: unknown) {
      setMessage(error instanceof Error ? error.message : "Directory sync failed.");
    } finally {
      setBusy("");
    }
  };

  return (
    <div className="max-w-5xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Sync Controls</h1>
        <p className="text-slate-600 mt-2">Central controls for classroom and directory synchronization workflows.</p>
      </header>

      {message ? (
        <div className="rounded-lg border border-sky-200 bg-sky-50 px-4 py-3 text-sm text-sky-800">{message}</div>
      ) : null}

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200 flex flex-wrap gap-3">
        <button onClick={runClassroomSync} disabled={busy.length > 0} className="rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-60">
          {busy === "classroom" ? "Syncing Classroom…" : "Run Classroom Sync"}
        </button>
        <button onClick={runDirectorySync} disabled={busy.length > 0} className="rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50 disabled:opacity-60">
          {busy === "directory" ? "Syncing Directory…" : "Run Directory Sync"}
        </button>
      </section>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h2 className="font-semibold text-lg text-slate-900">Directory Sync Status</h2>
        <p className="text-sm text-slate-600 mt-2">Total users: {stats?.total_directory_users ?? 0}</p>
        <p className="text-sm text-slate-600">Last completed sync: {stats?.latest_sync_job?.completed_at ? new Date(stats.latest_sync_job.completed_at).toLocaleString() : "Not available"}</p>
        {stats?.running_sync_job ? (
          <p className="text-sm text-slate-600 mt-1">In progress: {stats.running_sync_job.users_fetched_total} users over {stats.running_sync_job.pages_fetched} pages.</p>
        ) : null}
      </section>
    </div>
  );
}
