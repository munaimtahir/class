"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import GoogleScopePrompt from "../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../lib/api";

type DirectoryIssue = {
  id: number;
  severity: "critical" | "warning" | "info";
  status: string;
};

type DirectoryJob = {
  id: number;
  status: string;
  created_at: string;
};

type ProvisioningRecord = {
  id: number;
  status: string;
  created_at: string;
};

type SyncJob = {
  id: number;
  status: string;
  completed_at: string | null;
  pages_fetched: number;
  users_fetched_total: number;
};

type DirectoryStats = {
  total_directory_users: number;
  latest_sync_job: SyncJob | null;
  running_sync_job: SyncJob | null;
};

export default function DirectoryDashboardPage() {
  const [issues, setIssues] = useState<DirectoryIssue[]>([]);
  const [jobs, setJobs] = useState<DirectoryJob[]>([]);
  const [records, setRecords] = useState<ProvisioningRecord[]>([]);
  const [stats, setStats] = useState<DirectoryStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [scopeError, setScopeError] = useState<ApiError | null>(null);

  const load = async () => {
    setLoading(true);
    try {
      setScopeError(null);
      const [s, i, j, r] = await Promise.all([
        api.directoryStats(),
        api.listDirectoryIssues(),
        api.listDirectoryChangeJobs(),
        api.listProvisioningRecords(),
      ]);
      setStats(s || null);
      setIssues(i || []);
      setJobs(j || []);
      setRecords(r || []);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Failed to load dashboard.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    if (!stats?.running_sync_job) return;
    const timer = setInterval(() => {
      api.directoryStats().then((s) => setStats(s)).catch(() => null);
    }, 3000);
    return () => clearInterval(timer);
  }, [stats?.running_sync_job]);

  const summary = useMemo(() => {
    const critical = issues.filter((i) => i.severity === "critical").length;
    const warning = issues.filter((i) => i.severity === "warning").length;
    const info = issues.filter((i) => i.severity === "info").length;
    const pendingReview = issues.filter((i) => i.status === "detected").length;
    const lastSync = stats?.latest_sync_job?.completed_at || null;
    return { critical, warning, info, pendingReview, lastSync };
  }, [issues, stats]);

  const handleSync = async () => {
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const result = await api.syncDirectory({});
      setMsg(
        `Directory sync complete: ${result.synced} users across ${result.pages_fetched} pages (${result.created} new, ${result.updated} updated).`,
      );
      await load();
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Directory sync failed.");
    } finally {
      setBusy(false);
    }
  };

  const handleScan = async () => {
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const result = await api.scanDirectoryIssues({});
      setMsg(`Issue scan complete: ${result.issues_created} issues across ${result.users_scanned} users.`);
      await load();
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Issue scan failed.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <h1 style={{ margin: 0 }}>Directory Dashboard</h1>
        <div style={{ display: "flex", gap: 8 }}>
          <button onClick={handleSync} disabled={busy} style={btnPrimary}>
            {busy ? "Working…" : "Sync Directory"}
          </button>
          <button onClick={handleScan} disabled={busy} style={btnOutline}>
            Scan Issues
          </button>
        </div>
      </div>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Read-only sync + verification + rule validation + controlled fix/provisioning workflows.
      </p>
      {msg && <div style={notice}>{msg}</div>}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      {loading ? (
        <p>Loading…</p>
      ) : (
        <>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(190px, 1fr))", gap: 12 }}>
            <StatCard label="Synced users" value={stats?.total_directory_users || 0} />
            <StatCard label="Critical issues" value={summary.critical} tone="#b91c1c" />
            <StatCard label="Warning issues" value={summary.warning} tone="#92400e" />
            <StatCard label="Info issues" value={summary.info} tone="#1d4ed8" />
            <StatCard label="Pending review" value={summary.pendingReview} tone="#4338ca" />
            <StatCard label="Change jobs" value={jobs.length} />
            <StatCard label="Provisioning records" value={records.length} />
          </div>

          <div style={{ marginTop: 14, fontSize: 13, color: "#374151" }}>
            <b>Last sync:</b>{" "}
            {summary.lastSync ? new Date(summary.lastSync).toLocaleString() : "No sync timestamp available"}
          </div>
          {stats?.running_sync_job ? (
            <div style={{ marginTop: 6, fontSize: 13, color: "#1f2937" }}>
              <b>Sync in progress:</b> fetched {stats.running_sync_job.users_fetched_total} users across{" "}
              {stats.running_sync_job.pages_fetched} pages.
            </div>
          ) : null}

          <div style={{ marginTop: 20, display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
            <NavTile href="/admin/directory/users" title="Directory Users" />
            <NavTile href="/admin/directory/verification" title="Directory Verification" />
            <NavTile href="/admin/directory/issues" title="Inconsistency Review" />
            <NavTile href="/admin/directory/rules" title="OU & Email Rules" />
            <NavTile href="/admin/directory/approvals" title="Approval Requests" />
            <NavTile href="/admin/directory/provisioning" title="Create New IDs" />
            <NavTile href="/admin/directory/jobs" title="Operations Log" />
          </div>
        </>
      )}
    </div>
  );
}

function StatCard({ label, value, tone = "#111827" }: { label: string; value: number; tone?: string }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 10, padding: 14, background: "#fff" }}>
      <div style={{ fontSize: 12, color: "#6b7280" }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 700, color: tone }}>{value}</div>
    </div>
  );
}

function NavTile({ href, title }: { href: string; title: string }) {
  return (
    <Link href={href} style={{ textDecoration: "none", color: "#1d4ed8" }}>
      <div style={{ border: "1px solid #dbeafe", borderRadius: 8, padding: 12, background: "#eff6ff", fontWeight: 600 }}>
        {title}
      </div>
    </Link>
  );
}

const btnPrimary: React.CSSProperties = {
  padding: "8px 12px",
  background: "#1d4ed8",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  cursor: "pointer",
};
const btnOutline: React.CSSProperties = {
  padding: "8px 12px",
  background: "#fff",
  color: "#1f2937",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  cursor: "pointer",
};
const notice: React.CSSProperties = {
  marginBottom: 12,
  padding: "8px 12px",
  background: "#f0f9ff",
  borderRadius: 6,
  fontSize: 13,
};
