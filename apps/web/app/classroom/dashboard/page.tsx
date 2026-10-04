"use client";

import { useEffect, useRef, useState } from "react";

import { api } from "../../../lib/api";

type Course = { id: number; google_course_id: string; name: string; section: string };
type Session = {
  id: number;
  course: number;
  date: string;
  start_time: string;
  end_time: string;
  title: string;
  topic: string;
  subject: string;
  group: string;
  meet_required: boolean;
  post_type: "material" | "announcement";
  status: string;
  meet_link: string;
  calendar_event_id: string;
};
type Log = { id: number; session: number; status: string; message: string; created_at: string };

const initialSession = {
  course: "",
  date: "",
  start_time: "",
  end_time: "",
  title: "",
  topic: "",
  subject: "",
  group: "",
  meet_required: true,
  post_type: "material",
};

export default function ClassroomDashboardPage() {
  const [auth, setAuth] = useState<{ authenticated: boolean; user?: { name: string; email: string } } | null>(null);
  const [courses, setCourses] = useState<Course[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [logs, setLogs] = useState<Log[]>([]);
  const [selectedCourse, setSelectedCourse] = useState<string>("");
  const [selected, setSelected] = useState<number[]>([]);
  const [form, setForm] = useState<Record<string, string | boolean>>(initialSession);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [lastLogSyncAt, setLastLogSyncAt] = useState<Date | null>(null);
  const liveSyncInFlight = useRef(false);

  async function refreshAuthenticatedData() {
    const [courseData, sessionData, logData] = await Promise.all([api.courses(), api.sessions(), api.logs()]);
    setCourses(courseData);
    setSessions(sessionData);
    setLogs(
      [...logData].sort(
        (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      )
    );
    setLastLogSyncAt(new Date());
  }

  async function refresh() {
    const status = await api.authStatus();
    setAuth(status);
    if (status.authenticated) {
      await refreshAuthenticatedData();
    }
  }

  useEffect(() => {
    refresh().catch(console.error);
  }, []);

  useEffect(() => {
    if (!auth?.authenticated) {
      return;
    }
    const poll = async () => {
      if (liveSyncInFlight.current) {
        return;
      }
      liveSyncInFlight.current = true;
      try {
        const [sessionData, logData] = await Promise.all([api.sessions(), api.logs()]);
        setSessions(sessionData);
        setLogs(
          [...logData].sort(
            (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
          )
        );
        setLastLogSyncAt(new Date());
      } catch (err) {
        console.error(err);
      } finally {
        liveSyncInFlight.current = false;
      }
    };

    const id = window.setInterval(poll, 5000);
    return () => window.clearInterval(id);
  }, [auth?.authenticated]);

  async function handleLogin() {
    const { auth_url } = await api.authStart();
    window.location.href = auth_url;
  }

  async function saveSession() {
    setLoading(true);
    try {
      const payload = {
        ...form,
        course: Number(form.course),
      };
      if (editingId) {
        await api.updateSession(editingId, payload);
      } else {
        await api.createSession(payload);
      }
      setForm(initialSession);
      setEditingId(null);
      await refresh();
    } finally {
      setLoading(false);
    }
  }

  if (!auth || !auth.authenticated) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-amber-50 p-6 flex items-center justify-center">
        <section className="max-w-xl w-full rounded-2xl bg-white shadow-xl p-8 border border-slate-200">
          <h1 className="text-3xl font-bold text-slate-900">class</h1>
          <p className="mt-2 text-slate-600">Classroom Schedule Integrator</p>
          <button
            onClick={handleLogin}
            className="mt-6 rounded-lg bg-primary text-white px-4 py-2 hover:bg-teal-700"
          >
            Login with Google
          </button>
        </section>
      </main>
    );
  }

  const visibleSessions = selectedCourse
    ? sessions.filter((s) => String(s.course) === selectedCourse)
    : sessions;

  return (
    <main className="min-h-screen p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Classroom Dashboard</h1>
              <p className="text-slate-600">{auth.user?.name} ({auth.user?.email})</p>
            </div>
          <div className="flex items-center gap-3">
            <a
              href="/classroom/import-sessions"
              className="rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-4 py-2 text-sm font-semibold"
            >
              Import Timetable
            </a>
            <a
              href="/classroom/publish-planner"
              className="rounded-lg bg-slate-800 hover:bg-slate-900 text-white px-4 py-2 text-sm font-semibold"
            >
              Post Day Timetable
            </a>
          </div>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
            <Stat label="Total sessions" value={sessions.length} />
            <Stat label="Scheduled posts" value={sessions.filter((s) => s.status === "scheduled").length} />
            <Stat label="Posted" value={sessions.filter((s) => s.status === "posted").length} />
            <Stat label="Failed" value={sessions.filter((s) => s.status === "failed").length} />
          </div>
        </header>

        <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
          <h2 className="font-semibold text-lg">Course Selector</h2>
          <div className="flex gap-3 mt-3">
            <select
              aria-label="Course filter"
              value={selectedCourse}
              onChange={(e) => setSelectedCourse(e.target.value)}
              className="border rounded px-3 py-2"
            >
              <option value="">All courses</option>
              {courses.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.name} {c.section ? `(${c.section})` : ""}
                </option>
              ))}
            </select>
            <button
              className="rounded bg-slate-800 text-white px-3 py-2"
              onClick={async () => {
                await api.syncCourses();
                await refresh();
              }}
            >
              Sync Classrooms
            </button>
          </div>
        </section>

        <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
          <h2 className="font-semibold text-lg">Session Manager</h2>
          <div className="grid md:grid-cols-4 gap-2 mt-3">
            <select
              aria-label="Session course"
              value={String(form.course)}
              onChange={(e) => setForm((f) => ({ ...f, course: e.target.value }))}
              className="border rounded px-3 py-2"
            >
              <option value="">Course</option>
              {courses.map((c) => (
                <option key={c.id} value={String(c.id)}>
                  {c.name}
                </option>
              ))}
            </select>
            <input aria-label="Session date" type="date" className="border rounded px-3 py-2" value={String(form.date)} onChange={(e) => setForm((f) => ({ ...f, date: e.target.value }))} />
            <input aria-label="Session start time" type="time" className="border rounded px-3 py-2" value={String(form.start_time)} onChange={(e) => setForm((f) => ({ ...f, start_time: e.target.value }))} />
            <input aria-label="Session end time" type="time" className="border rounded px-3 py-2" value={String(form.end_time)} onChange={(e) => setForm((f) => ({ ...f, end_time: e.target.value }))} />
            <input aria-label="Session title" placeholder="Title" className="border rounded px-3 py-2" value={String(form.title)} onChange={(e) => setForm((f) => ({ ...f, title: e.target.value }))} />
            <input aria-label="Session topic" placeholder="Topic" className="border rounded px-3 py-2" value={String(form.topic)} onChange={(e) => setForm((f) => ({ ...f, topic: e.target.value }))} />
            <input aria-label="Session subject" placeholder="Subject" className="border rounded px-3 py-2" value={String(form.subject)} onChange={(e) => setForm((f) => ({ ...f, subject: e.target.value }))} />
            <input aria-label="Session group" placeholder="Group" className="border rounded px-3 py-2" value={String(form.group)} onChange={(e) => setForm((f) => ({ ...f, group: e.target.value }))} />
            <label className="flex items-center gap-2 text-sm col-span-2">
              <input
                type="checkbox"
                checked={Boolean(form.meet_required)}
                onChange={(e) => setForm((f) => ({ ...f, meet_required: e.target.checked }))}
              />
              Meet required
            </label>
            <select
              aria-label="Post type"
              className="border rounded px-3 py-2"
              value={String(form.post_type)}
              onChange={(e) => setForm((f) => ({ ...f, post_type: e.target.value }))}
            >
              <option value="material">Material</option>
              <option value="announcement">Announcement</option>
            </select>
            <button disabled={loading} onClick={saveSession} className="rounded bg-primary text-white px-3 py-2">
              {editingId ? "Save Session" : "Add Session"}
            </button>
            {editingId ? (
              <button
                className="rounded bg-slate-500 text-white px-3 py-2"
                onClick={() => {
                  setEditingId(null);
                  setForm(initialSession);
                }}
              >
                Cancel
              </button>
            ) : null}
          </div>

          <div className="overflow-auto mt-4">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b">
                  <th className="p-2 text-left"></th>
                  <th className="p-2 text-left">Title</th>
                  <th className="p-2 text-left">Date</th>
                  <th className="p-2 text-left">Time</th>
                  <th className="p-2 text-left">Meet</th>
                  <th className="p-2 text-left">Status</th>
                  <th className="p-2 text-left">Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleSessions.map((s) => (
                  <tr key={s.id} className="border-b">
                    <td className="p-2">
                      <input
                        aria-label={`Select session ${s.title}`}
                        type="checkbox"
                        checked={selected.includes(s.id)}
                        onChange={(e) =>
                          setSelected((prev) =>
                            e.target.checked ? [...prev, s.id] : prev.filter((id) => id !== s.id)
                          )
                        }
                      />
                    </td>
                    <td className="p-2">{s.title}</td>
                    <td className="p-2">{s.date}</td>
                    <td className="p-2">{s.start_time} - {s.end_time}</td>
                    <td className="p-2">
                      {s.meet_link ? (
                        <a
                          href={s.meet_link}
                          target="_blank"
                          rel="noreferrer"
                          className="text-teal-700 underline underline-offset-2"
                        >
                          Open link
                        </a>
                      ) : (
                        <span className="text-slate-400">{s.meet_required ? "Not generated" : "Not required"}</span>
                      )}
                    </td>
                    <td className="p-2 capitalize">{s.status}</td>
                    <td className="p-2">
                      <button
                        className="text-slate-700 mr-3"
                        onClick={() => {
                          setEditingId(s.id);
                          setForm({
                            course: String(s.course),
                            date: s.date,
                            start_time: s.start_time.slice(0, 5),
                            end_time: s.end_time.slice(0, 5),
                            title: s.title,
                            topic: s.topic,
                            subject: s.subject,
                            group: s.group,
                            meet_required: s.meet_required,
                            post_type: s.post_type,
                          });
                        }}
                      >
                        Edit
                      </button>
                      <button
                        className="text-red-700"
                        onClick={async () => {
                          await api.deleteSession(s.id);
                          await refresh();
                        }}
                      >
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
          <h2 className="font-semibold text-lg">Publish Panel</h2>
          <div className="flex flex-wrap gap-3 mt-3">
            <button
              className="rounded bg-amber-500 text-white px-3 py-2"
              onClick={async () => {
                await api.generateMeet(selected);
                await refreshAuthenticatedData();
              }}
            >
              Generate Meet Links
            </button>
            <button
              className="rounded bg-slate-900 text-white px-3 py-2"
              onClick={async () => {
                await api.schedulePosts(selected);
                await refreshAuthenticatedData();
              }}
            >
              Schedule Posts
            </button>
            <button
              className="rounded bg-primary text-white px-3 py-2"
              onClick={async () => {
                await api.publishNow(selected);
                await refreshAuthenticatedData();
              }}
            >
              Publish Now
            </button>
          </div>
        </section>

        <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
          <h2 className="font-semibold text-lg">Logs</h2>
          <p className="text-xs text-slate-500 mt-1">
            Live updates every 5s
            {lastLogSyncAt ? ` - Last sync: ${lastLogSyncAt.toLocaleTimeString()}` : ""}
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {logs.map((log) => (
              <li key={log.id} className="border rounded p-2 bg-slate-50">
                Session #{log.session} - <span className="font-semibold capitalize">{log.status}</span> - {log.message}
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-slate-200 p-3 bg-slate-50">
      <p className="text-xs text-slate-600">{label}</p>
      <p className="text-2xl font-bold">{value}</p>
    </div>
  );
}
