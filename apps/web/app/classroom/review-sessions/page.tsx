"use client";

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

export default function ClassroomReviewSessionsPage() {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.sessions().then((data) => setSessions(data || [])).finally(() => setLoading(false));
  }, []);

  const reviewQueue = useMemo(
    () =>
      sessions.filter(
        (s) =>
          s.status === "failed" ||
          (s.meet_required && !s.meet_link) ||
          ["scheduled", "pending"].includes((s.status || "").toLowerCase()),
      ),
    [sessions],
  );

  return (
    <div className="max-w-6xl space-y-4">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Review Sessions</h1>
        <p className="text-slate-600 mt-2">
          Focused review queue for sessions with missing Meet links, pending schedules, or failed posting outcomes.
        </p>
      </header>

      <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
        {loading ? (
          <p className="text-slate-500">Loading review queue…</p>
        ) : reviewQueue.length === 0 ? (
          <p className="text-slate-600">No sessions currently require review.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b bg-slate-50">
                <th className="text-left p-2">Session</th>
                <th className="text-left p-2">Date</th>
                <th className="text-left p-2">Status</th>
                <th className="text-left p-2">Review Reason</th>
              </tr>
            </thead>
            <tbody>
              {reviewQueue.map((session) => {
                const reason = session.status === "failed"
                  ? "Publish failed"
                  : session.meet_required && !session.meet_link
                    ? "Meet link missing"
                    : "Pending publish state";
                return (
                  <tr key={session.id} className="border-b">
                    <td className="p-2">{session.title}</td>
                    <td className="p-2">{session.date}</td>
                    <td className="p-2 capitalize">{session.status}</td>
                    <td className="p-2">{reason}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
