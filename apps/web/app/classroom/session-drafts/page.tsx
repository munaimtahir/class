"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { api } from "../../../lib/api";

type Session = {
  id: number;
  title: string;
  date: string;
  start_time: string;
  end_time: string;
  status: string;
  meet_required: boolean;
  meet_link: string;
};

export default function ClassroomSessionDraftsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sessions().then((data) => setSessions(data || [])).finally(() => setLoading(false));
  }, []);

  const drafts = useMemo(
    () => sessions.filter((s) => ["draft", "pending", "new"].includes((s.status || "").toLowerCase())),
    [sessions],
  );

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Session Drafts</h1>
        <p className="text-slate-600 mt-2">Review draft/pending classroom sessions before publishing actions.</p>
      </header>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        {loading ? (
          <p className="text-slate-500">Loading drafts…</p>
        ) : drafts.length === 0 ? (
          <p className="text-slate-600">No draft sessions found. Use Classroom Dashboard to create/edit sessions.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left p-2">Title</th>
                <th className="text-left p-2">Date</th>
                <th className="text-left p-2">Time</th>
                <th className="text-left p-2">Status</th>
              </tr>
            </thead>
            <tbody>
              {drafts.map((session) => (
                <tr key={session.id} className="border-b">
                  <td className="p-2">{session.title}</td>
                  <td className="p-2">{session.date}</td>
                  <td className="p-2">{session.start_time} - {session.end_time}</td>
                  <td className="p-2 capitalize">{session.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="mt-4">
          <Link href="/classroom/dashboard" className="text-sm text-slate-700 underline underline-offset-2">
            Open Classroom Dashboard
          </Link>
        </div>
      </section>
    </div>
  );
}
