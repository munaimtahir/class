"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

type Job = {
  id: number;
  job_type: string;
  created_by_email: string | null;
  status: string;
  dry_run: boolean;
  item_count: number;
  target_summary_json: Record<string, unknown>;
  result_summary_json?: Record<string, unknown>;
  created_at: string;
};

type JobDetail = Job & {
  items: Item[];
};

type Item = {
  id: number;
  target_type: string;
  target_ref: string;
  action: string;
  status: string;
  result_json: Record<string, unknown>;
  retry_count: number;
  created_at: string;
};

type CommandLog = {
  id: number;
  actor_email?: string;
  action_type?: string;
  job?: number;
  detail?: string;
  created_at: string;
};

const STATUS_COLOR: Record<string, string> = {
  pending: "#f59e0b",
  running: "#3b82f6",
  completed: "#16a34a",
  partial: "#f97316",
  failed: "#dc2626",
  dry_run: "#8b5cf6",
  success: "#16a34a",
  skipped: "#6b7280",
  retrying: "#f59e0b",
};

const ACTION_LABELS: Record<string, string> = {
  ADD_USER_TO_GROUP: "Add to Group",
  REMOVE_USER_FROM_GROUP: "Remove from Group",
  ADD_STUDENT_TO_COURSE: "Add Student",
  ADD_TEACHER_TO_COURSE: "Add Teacher",
  ENROLL_GROUP_TO_COURSE: "Enroll Group",
  APPLY_ONBOARDING_BUNDLE: "Apply Bundle",
  BULK_CSV_ONBOARDING: "CSV Onboarding",
  // Phase 2B
  CREATE_COURSE: "Create Course",
  ARCHIVE_COURSE: "Archive Course",
  DELETE_COURSE: "Delete Course",
  REMOVE_STUDENT_FROM_COURSE: "Remove Student",
  REMOVE_TEACHER_FROM_COURSE: "Remove Teacher",
};

function actionLabel(t: string) {
  return ACTION_LABELS[t] ?? t;
}

type Tab = "jobs" | "logs";

export default function JobsPage() {
  const [tab, setTab] = useState<Tab>("jobs");
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedJob, setSelectedJob] = useState<JobDetail | null>(null);
  const [jobLoading, setJobLoading] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [msg, setMsg] = useState("");

  // Command logs state
  const [logs, setLogs] = useState<CommandLog[]>([]);
  const [logsLoading, setLogsLoading] = useState(false);

  const loadJobs = () => {
    setLoading(true);
    api.listJobs().then(setJobs).catch(() => setMsg("Failed to load jobs.")).finally(() => setLoading(false));
  };

  const loadLogs = () => {
    setLogsLoading(true);
    api.commandLogs().then((d) => setLogs(Array.isArray(d) ? d : d.results ?? [])).catch(() => setMsg("Failed to load logs.")).finally(() => setLogsLoading(false));
  };

  useEffect(() => { loadJobs(); }, []);

  useEffect(() => {
    if (tab === "logs" && logs.length === 0) loadLogs();
  }, [tab]);

  const handleViewJob = async (job: Job) => {
    setJobLoading(true);
    setSelectedJob(null);
    try {
      const detail = await api.getJob(job.id);
      setSelectedJob(detail);
    } catch {
      setMsg("Failed to load job details.");
    } finally {
      setJobLoading(false);
    }
  };

  const handleRetry = async (jobId: number) => {
    setRetrying(true);
    setMsg("");
    try {
      await api.retryJob(jobId);
      setMsg(`Retry queued for job #${jobId}.`);
      loadJobs();
    } catch {
      setMsg("Retry failed.");
    } finally {
      setRetrying(false);
    }
  };

  const hasFailed = (job: Job) => {
    const failed = (job.result_summary_json?.failed as number | undefined) ?? 0;
    return failed > 0;
  };

  const tabStyle = (t: Tab): React.CSSProperties => ({
    padding: "7px 18px",
    border: "none",
    borderBottom: t === tab ? "2px solid #2563eb" : "2px solid transparent",
    background: "none",
    cursor: "pointer",
    fontSize: 14,
    fontWeight: t === tab ? 700 : 400,
    color: t === tab ? "#2563eb" : "#555",
  });

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4 }}>
        <h1 style={{ margin: 0 }}>Jobs & Logs</h1>
        <button
          onClick={() => { if (tab === "jobs") loadJobs(); else loadLogs(); }}
          style={{ padding: "7px 14px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer", fontSize: 13 }}
        >
          Refresh
        </button>
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: "1px solid #e5e7eb", marginBottom: 16, display: "flex", gap: 4 }}>
        <button style={tabStyle("jobs")} onClick={() => setTab("jobs")}>Command Jobs</button>
        <button style={tabStyle("logs")} onClick={() => setTab("logs")}>Audit Logs</button>
      </div>

      {msg && <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 }}>{msg}</div>}

      {/* Jobs Tab */}
      {tab === "jobs" && (
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div style={{ flex: "1 1 500px" }}>
            {loading ? (
              <p>Loading…</p>
            ) : jobs.length === 0 ? (
              <p style={{ color: "#666" }}>No jobs yet. Use the Command Runner to create one.</p>
            ) : (
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f3f4f6" }}>
                    <th style={th}>ID</th>
                    <th style={th}>Type</th>
                    <th style={th}>Status</th>
                    <th style={th}>Items</th>
                    <th style={th}>Dry Run</th>
                    <th style={th}>Created</th>
                    <th style={th}>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {jobs.map((job) => (
                    <tr key={job.id} style={{ borderBottom: "1px solid #e5e7eb", background: selectedJob?.id === job.id ? "#eff6ff" : undefined }}>
                      <td style={td}>#{job.id}</td>
                      <td style={td}><span style={{ fontSize: 11 }}>{actionLabel(job.job_type)}</span></td>
                      <td style={td}>
                        <span style={{
                          padding: "2px 8px", borderRadius: 9999, fontSize: 11, fontWeight: 600,
                          background: `${STATUS_COLOR[job.status]}22`,
                          color: STATUS_COLOR[job.status] || "#374151",
                        }}>
                          {job.status}
                        </span>
                      </td>
                      <td style={td}>{job.item_count}</td>
                      <td style={td}>{job.dry_run ? "✓" : ""}</td>
                      <td style={td}>{new Date(job.created_at).toLocaleString()}</td>
                      <td style={td}>
                        <div style={{ display: "flex", gap: 6 }}>
                          <button onClick={() => handleViewJob(job)} style={btnSm}>Details</button>
                          {hasFailed(job) && (
                            <button
                              onClick={() => handleRetry(job.id)}
                              disabled={retrying}
                              style={{ ...btnSm, background: "#fee2e2" }}
                            >
                              Retry
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {(selectedJob || jobLoading) && (
            <div style={{ flex: "0 0 400px", border: "1px solid #d1d5db", borderRadius: 8, padding: 20, maxHeight: 600, overflow: "auto" }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 12 }}>
                <h3 style={{ margin: 0, fontSize: 14 }}>Job #{selectedJob?.id} Details</h3>
                <button onClick={() => setSelectedJob(null)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18 }}>×</button>
              </div>
              {jobLoading ? (
                <p>Loading…</p>
              ) : selectedJob && (
                <>
                  <div style={{ fontSize: 12, marginBottom: 12, padding: 10, background: "#f9fafb", borderRadius: 6 }}>
                    <div><b>Type:</b> {actionLabel(selectedJob.job_type)}</div>
                    <div><b>Status:</b> {selectedJob.status}</div>
                    <div><b>Created by:</b> {selectedJob.created_by_email || "—"}</div>
                    {Object.keys(selectedJob.result_summary_json || {}).length > 0 && (
                      <div><b>Result:</b> {JSON.stringify(selectedJob.result_summary_json || {})}</div>
                    )}
                  </div>
                  <h4 style={{ margin: "0 0 8px", fontSize: 13 }}>Items ({selectedJob.items?.length || 0})</h4>
                  {(selectedJob.items || []).map((item) => (
                    <div key={item.id} style={{ marginBottom: 8, padding: "8px 10px", border: "1px solid #e5e7eb", borderRadius: 6, fontSize: 12 }}>
                      <div style={{ display: "flex", justifyContent: "space-between" }}>
                        <span>{actionLabel(item.action)}</span>
                        <span style={{ color: STATUS_COLOR[item.status] || "#374151", fontWeight: 600 }}>{item.status}</span>
                      </div>
                      <div style={{ color: "#555" }}>{item.target_ref}</div>
                      {item.result_json && Object.keys(item.result_json).length > 0 && (
                        <div style={{ color: "#777", marginTop: 2 }}>{JSON.stringify(item.result_json)}</div>
                      )}
                    </div>
                  ))}
                </>
              )}
            </div>
          )}
        </div>
      )}

      {/* Audit Logs Tab */}
      {tab === "logs" && (
        <div>
          {logsLoading ? (
            <p>Loading logs…</p>
          ) : logs.length === 0 ? (
            <p style={{ color: "#666" }}>No command audit logs yet.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f3f4f6" }}>
                  <th style={th}>#</th>
                  <th style={th}>Actor</th>
                  <th style={th}>Action</th>
                  <th style={th}>Job</th>
                  <th style={th}>Detail</th>
                  <th style={th}>Time</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log) => (
                  <tr key={log.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={td}>{log.id}</td>
                    <td style={td}>{log.actor_email || "—"}</td>
                    <td style={td}>{log.action_type ? actionLabel(log.action_type) : "—"}</td>
                    <td style={td}>{log.job ? `#${log.job}` : "—"}</td>
                    <td style={{ ...td, maxWidth: 300, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{log.detail || "—"}</td>
                    <td style={td}>{new Date(log.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 12px", fontWeight: 600, fontSize: 12, color: "#374151" };
const td: React.CSSProperties = { padding: "8px 12px", verticalAlign: "middle" };
const btnSm: React.CSSProperties = { fontSize: 12, padding: "3px 10px", background: "#e0e7ff", border: "none", borderRadius: 4, cursor: "pointer" };

