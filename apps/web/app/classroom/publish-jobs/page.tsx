"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "../../../lib/api";

type Session = {
  id: number;
  title: string;
  date: string;
  status: string;
};

export default function ClassroomPublishJobsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sessions().then((data) => setSessions(data || [])).finally(() => setLoading(false));
  }, []);

  const stats = useMemo(() => ({
    scheduled: sessions.filter((s) => s.status === "scheduled").length,
    posted: sessions.filter((s) => s.status === "posted").length,
    failed: sessions.filter((s) => s.status === "failed").length,
  }), [sessions]);

  const publishRelated = useMemo(() => sessions.filter((s) => ["scheduled", "posted", "failed"].includes(s.status)), [sessions]);

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Publish Jobs</h1>
        <p className="text-slate-600 mt-2">Operational summary for scheduled, posted, and failed classroom publishing runs.</p>
      </header>

      <section className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <StatCard label="Scheduled" value={stats.scheduled} />
        <StatCard label="Posted" value={stats.posted} />
        <StatCard label="Failed" value={stats.failed} tone="text-rose-700" />
      </section>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        {loading ? (
          <p className="text-slate-500">Loading publish jobs…</p>
        ) : publishRelated.length === 0 ? (
          <p className="text-slate-600">No publish jobs found yet.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left p-2">Session</th>
                <th className="text-left p-2">Date</th>
                <th className="text-left p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {publishRelated.map((session) => (
                <tr key={session.id} className="border-b">
                  <td className="p-2">{session.title}</td>
                  <td className="p-2">{session.date}</td>
                  <td className="p-2 capitalize">{session.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

function StatCard({ label, value, tone = "text-slate-900" }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow border border-slate-200">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold mt-1 ${tone}`}>{value}</p>
    </div>
  );
}
