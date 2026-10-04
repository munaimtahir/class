"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import {
  loadWorkspaceDashboardData,
  type WorkspaceDashboardData,
} from "../lib/workspaceDashboardAdapter";

export default function WorkspaceHomePage() {
  const [auth, setAuth] = useState<{
    authenticated: boolean;
    user?: { name: string; email: string };
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const [data, setData] = useState<WorkspaceDashboardData | null>(null);
  const [errorText, setErrorText] = useState("");

  useEffect(() => {
    let cancelled = false;
    const load = async () => {
      try {
        const status = await api.authStatus();
        if (cancelled) {
          return;
        }
        setAuth(status);
        if (!status.authenticated) {
          setData(null);
          return;
        }
        const overview = await loadWorkspaceDashboardData();
        if (!cancelled) {
          setData(overview);
        }
      } catch (error: unknown) {
        if (!cancelled) {
          setErrorText(error instanceof Error ? error.message : "Failed to load workspace dashboard.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load().catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, []);

  async function handleLogin() {
    const { auth_url } = await api.authStart();
    window.location.href = auth_url;
  }

  if (!auth || !auth.authenticated) {
    return (
      <main className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-amber-50 p-6 flex items-center justify-center">
        <section className="max-w-xl w-full rounded-2xl bg-white shadow-xl p-8 border border-slate-200">
          <h1 className="text-3xl font-bold text-slate-900">CLASS</h1>
          <p className="mt-2 text-slate-600">Workspace Operations Dashboard</p>
          <p className="mt-3 text-sm text-slate-500">
            Sign in with your institutional Google Workspace account to continue.
          </p>
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

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      <header className="rounded-xl bg-white p-5 shadow border border-slate-200">
        <h1 className="text-2xl font-bold text-slate-900">Workspace Dashboard</h1>
        <p className="text-slate-600 mt-1">
          Cross-module operational health for Classroom, Directory, and issue resolution workflows.
        </p>
        <p className="text-sm text-slate-500 mt-1">
          {auth.user?.name} ({auth.user?.email})
        </p>
      </header>

      {errorText ? (
        <div className="rounded-lg border border-amber-300 bg-amber-50 px-4 py-3 text-amber-900 text-sm">
          {errorText}
        </div>
      ) : null}

      {loading ? (
        <section className="rounded-xl bg-white p-5 shadow border border-slate-200 text-slate-500">
          Loading workspace metrics…
        </section>
      ) : data ? (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-5 gap-3">
            <MetricCard label="Connection Status" value={data.connectionStatus} />
            <MetricCard label="Directory Sync Status" value={data.directorySyncStatus} />
            <MetricCard label="Synced Users" value={String(data.totalSyncedUsers)} />
            <MetricCard label="Active Courses" value={String(data.totalActiveCourses)} />
            <MetricCard label="Unresolved Issues" value={String(data.unresolvedIssues)} />
          </section>

          <section className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3">
            <MetricCard
              label="Last Workspace Sync"
              value={data.lastWorkspaceSync ? new Date(data.lastWorkspaceSync).toLocaleString() : "Not yet synced"}
            />
            <MetricCard
              label="Last Classroom Sync"
              value={data.lastClassroomSync ? new Date(data.lastClassroomSync).toLocaleString() : "No activity yet"}
            />
            <MetricCard label="Pending Publish Jobs" value={String(data.pendingPublishJobs)} />
            <MetricCard label="Failed Publish Jobs" value={String(data.failedPublishJobs)} />
          </section>

          <section className="grid grid-cols-1 xl:grid-cols-2 gap-4">
            <Panel title="Recent Activity">
              <ul className="space-y-2">
                {data.recentActivity.map((item, index) => (
                  <li
                    key={`${item.title}-${index}`}
                    className={`rounded-lg px-3 py-2 text-sm ${
                      item.tone === "danger"
                        ? "bg-rose-50 border border-rose-200 text-rose-800"
                        : item.tone === "warning"
                          ? "bg-amber-50 border border-amber-200 text-amber-900"
                          : "bg-slate-50 border border-slate-200 text-slate-700"
                    }`}
                  >
                    <p className="font-semibold">{item.title}</p>
                    <p>{item.detail}</p>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel title="Warnings / Alerts">
              <ul className="space-y-2">
                {data.alerts.map((alert, index) => (
                  <li
                    key={`${alert.title}-${index}`}
                    className={`rounded-lg px-3 py-2 text-sm ${
                      alert.severity === "critical"
                        ? "bg-rose-50 border border-rose-200 text-rose-800"
                        : alert.severity === "warning"
                          ? "bg-amber-50 border border-amber-200 text-amber-900"
                          : "bg-sky-50 border border-sky-200 text-sky-800"
                    }`}
                  >
                    <p className="font-semibold">{alert.title}</p>
                    <p>{alert.detail}</p>
                  </li>
                ))}
              </ul>
            </Panel>
          </section>

          <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
            <h2 className="font-semibold text-lg text-slate-900">Operations Shortcuts</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-3 mt-3">
              <Shortcut href="/classroom/dashboard" title="Classroom Dashboard" />
              <Shortcut href="/directory/dashboard" title="Directory Dashboard" />
              <Shortcut href="/resolution/dashboard" title="Issues Dashboard" />
              <Shortcut href="/classroom/publish-jobs" title="Publish Jobs" />
              <Shortcut href="/directory/sync-history" title="Directory Sync History" />
              <Shortcut href="/administration/sync-controls" title="Sync Controls" />
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-white p-4 shadow border border-slate-200">
      <p className="text-xs text-slate-500">{label}</p>
      <p className="text-lg font-semibold text-slate-900 mt-1">{value}</p>
    </div>
  );
}

function Panel({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
      <h2 className="font-semibold text-lg text-slate-900">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

function Shortcut({ href, title }: { href: string; title: string }) {
  return (
    <Link href={href} className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-800 hover:bg-slate-50">
      {title}
    </Link>
  );
}
