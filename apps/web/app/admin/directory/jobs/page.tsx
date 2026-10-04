"use client";

import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

type ChangeJob = {
  id: number;
  job_type: string;
  scope_type: string;
  status: string;
  is_dry_run: boolean;
  execution_summary: Record<string, unknown>;
  created_at: string;
  item_count: number;
};

type AuditLog = {
  id: number;
  actor_email: string | null;
  action_type: string;
  target_ref: string;
  is_dry_run: boolean;
  success: boolean;
  created_at: string;
  error_message: string;
};

export default function DirectoryJobsPage() {
  const [tab, setTab] = useState<"jobs" | "audit">("jobs");
  const [jobs, setJobs] = useState<ChangeJob[]>([]);
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);
  const [requestingApprovalId, setRequestingApprovalId] = useState<number | null>(null);

  const loadJobs = async () => {
    setLoading(true);
    try {
      const res = await api.listDirectoryChangeJobs();
      setJobs(res || []);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to load jobs.");
    } finally {
      setLoading(false);
    }
  };

  const loadLogs = async () => {
    setLoading(true);
    try {
      const res = await api.listDirectoryAuditLogs();
      setLogs(res || []);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to load audit logs.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadJobs();
  }, []);

  const switchTab = (next: "jobs" | "audit") => {
    setTab(next);
    if (next === "jobs") loadJobs();
    if (next === "audit") loadLogs();
  };

  const requestJobApproval = async (job: ChangeJob) => {
    setRequestingApprovalId(job.id);
    setMsg("");
    try {
      const approval = await api.createDirectoryApprovalRequest({
        action_type: "bulk_change_job_execute",
        target_type: "change_job",
        target_reference: `change_job:${job.id}`,
        payload: { preview_job_id: job.id },
        linked_change_job_id: job.id,
      });
      setMsg(`Approval request #${approval.id} submitted for job #${job.id}.`);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to request job approval.");
    } finally {
      setRequestingApprovalId(null);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Operations Log</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Review dry-run and executed jobs with audit-aware mutation records.
      </p>
      {msg && <div style={notice}>{msg}</div>}

      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        <button onClick={() => switchTab("jobs")} style={tab === "jobs" ? btnPrimary : btnOutline}>
          Change Jobs
        </button>
        <button onClick={() => switchTab("audit")} style={tab === "audit" ? btnPrimary : btnOutline}>
          Audit Logs
        </button>
      </div>

      {loading ? (
        <p>Loading…</p>
      ) : tab === "jobs" ? (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th style={th}>ID</th>
              <th style={th}>Type</th>
              <th style={th}>Scope</th>
              <th style={th}>Status</th>
              <th style={th}>Dry-run</th>
              <th style={th}>Items</th>
              <th style={th}>Approval</th>
              <th style={th}>Summary</th>
              <th style={th}>Created</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((j) => (
              <tr key={j.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={td}>#{j.id}</td>
                <td style={td}>{j.job_type}</td>
                <td style={td}>{j.scope_type}</td>
                <td style={td}>{j.status}</td>
                <td style={td}>{j.is_dry_run ? "yes" : "no"}</td>
                <td style={td}>{j.item_count}</td>
                <td style={td}>
                  {j.scope_type === "bulk" && j.status === "preview_ready" ? (
                    <button
                      onClick={() => requestJobApproval(j)}
                      disabled={requestingApprovalId === j.id}
                      style={btnOutline}
                    >
                      {requestingApprovalId === j.id ? "Requesting…" : "Request Approval"}
                    </button>
                  ) : (
                    "—"
                  )}
                </td>
                <td style={td}>{JSON.stringify(j.execution_summary || {})}</td>
                <td style={td}>{new Date(j.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th style={th}>ID</th>
              <th style={th}>Actor</th>
              <th style={th}>Action</th>
              <th style={th}>Target</th>
              <th style={th}>Mode</th>
              <th style={th}>Result</th>
              <th style={th}>Error</th>
              <th style={th}>Time</th>
            </tr>
          </thead>
          <tbody>
            {logs.map((log) => (
              <tr key={log.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={td}>{log.id}</td>
                <td style={td}>{log.actor_email || "—"}</td>
                <td style={td}>{log.action_type}</td>
                <td style={td}>{log.target_ref || "—"}</td>
                <td style={td}>{log.is_dry_run ? "dry-run" : "execute"}</td>
                <td style={td}>{log.success ? "success" : "failed"}</td>
                <td style={td}>{log.error_message || "—"}</td>
                <td style={td}>{new Date(log.created_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: 12 };
const td: React.CSSProperties = { padding: "8px 10px" };
const btnPrimary: React.CSSProperties = { padding: "7px 12px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" };
const btnOutline: React.CSSProperties = { padding: "7px 12px", background: "#fff", color: "#1f2937", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" };
const notice: React.CSSProperties = { marginBottom: 10, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 };
