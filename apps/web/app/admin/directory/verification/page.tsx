"use client";

import { useEffect, useMemo, useState } from "react";
import GoogleScopePrompt from "../../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../../lib/api";

type SyncJob = {
  id: number;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  pages_fetched: number;
  users_fetched_total: number;
  users_upserted_total: number;
  users_created_total: number;
  users_updated_total: number;
  error_message: string;
};

type DirectoryStats = {
  total_directory_users: number;
  latest_sync_job: SyncJob | null;
  running_sync_job: SyncJob | null;
};

type VerifyJob = {
  id: number;
  source_filename: string;
  source_type: string;
  sheet_name: string;
  status: string;
  row_count: number;
  summary_json: Record<string, number>;
  column_mapping_json: Record<string, string>;
  created_at: string;
  completed_at: string | null;
};

type VerifyRow = {
  id: number;
  row_no: number;
  input_json: Record<string, string>;
  matched_email: string;
  matched_name: string;
  match_basis: string;
  verdict: string;
  notes: string;
};

type MappingPreview = {
  headers: string[];
  suggested_mapping: Record<string, string>;
  row_count: number;
  source_type: string;
  sheet_name: string;
  available_sheets: string[];
};

const CANONICAL_FIELDS: Array<{ key: string; label: string }> = [
  { key: "name", label: "Name" },
  { key: "roll_no", label: "Roll No" },
  { key: "email_address", label: "Email Address" },
  { key: "phone_number", label: "Phone Number" },
  { key: "official_email_issued", label: "Official Email Issued" },
  { key: "email_pmc", label: "Email PMC" },
];

export default function DirectoryVerificationPage() {
  const [stats, setStats] = useState<DirectoryStats | null>(null);
  const [jobs, setJobs] = useState<VerifyJob[]>([]);
  const [activeJob, setActiveJob] = useState<VerifyJob | null>(null);
  const [rows, setRows] = useState<VerifyRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [page, setPage] = useState(1);
  const [verdictFilter, setVerdictFilter] = useState("");
  const [loadingRows, setLoadingRows] = useState(false);

  const [file, setFile] = useState<File | null>(null);
  const [mappingPreview, setMappingPreview] = useState<MappingPreview | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [selectedSheet, setSelectedSheet] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [scopeError, setScopeError] = useState<ApiError | null>(null);

  const loadStats = async () => {
    try {
      setScopeError(null);
      const data = await api.directoryStats();
      setStats(data);
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Failed to load directory stats.");
    }
  };

  const loadJobs = async () => {
    try {
      setScopeError(null);
      const data = await api.listDirectoryVerifyJobs();
      setJobs(data || []);
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Failed to load verification jobs.");
    }
  };

  const loadRows = async (jobId: number, nextPage = 1, verdict = verdictFilter) => {
    setLoadingRows(true);
    try {
      setScopeError(null);
      const data = await api.listDirectoryVerifyRows(jobId, {
        page: String(nextPage),
        page_size: "25",
        ...(verdict ? { verdict } : {}),
      });
      setRows(data.results || []);
      setTotalRows(data.total || 0);
      setPage(data.page || nextPage);
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Failed to load verification rows.");
    } finally {
      setLoadingRows(false);
    }
  };

  useEffect(() => {
    loadStats();
    loadJobs();
  }, []);

  useEffect(() => {
    if (!stats?.running_sync_job) return;
    const timer = setInterval(() => {
      loadStats();
    }, 3000);
    return () => clearInterval(timer);
  }, [stats?.running_sync_job]);

  const handleSync = async () => {
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const result = await api.syncDirectory({});
      setMsg(
        `Directory sync complete: ${result.synced} users fetched across ${result.pages_fetched} pages (${result.created} new, ${result.updated} updated).`,
      );
      await loadStats();
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Directory sync failed.");
    } finally {
      setBusy(false);
    }
  };

  const analyzeUpload = async () => {
    if (!file) {
      setMsg("Select a CSV/XLSX file first.");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const result = await api.verifyDirectoryUpload(file, {
        ...(selectedSheet ? { sheet_name: selectedSheet } : {}),
      });
      if (!result.requires_mapping) {
        setMsg("Unexpected response: mapping metadata not returned.");
        return;
      }
      setMappingPreview(result);
      setMapping(result.suggested_mapping || {});
      setSelectedSheet(result.sheet_name || "");
      setMsg(`File analyzed: ${result.row_count} rows found. Confirm mapping and run verification.`);
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Failed to analyze uploaded file.");
    } finally {
      setBusy(false);
    }
  };

  const runVerification = async () => {
    if (!file || !mappingPreview) {
      setMsg("Analyze a file and configure mapping first.");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const job = await api.verifyDirectoryUpload(file, {
        ...(selectedSheet ? { sheet_name: selectedSheet } : {}),
        mapping,
      });
      setActiveJob(job);
      setVerdictFilter("");
      setPage(1);
      await Promise.all([loadJobs(), loadRows(job.id, 1, "")]);
      setMsg(`Verification completed for ${job.row_count} rows.`);
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Verification failed.");
    } finally {
      setBusy(false);
    }
  };

  const changeJob = async (job: VerifyJob) => {
    setActiveJob(job);
    setVerdictFilter("");
    await loadRows(job.id, 1, "");
  };

  const applyVerdictFilter = async (nextVerdict: string) => {
    setVerdictFilter(nextVerdict);
    if (!activeJob) return;
    await loadRows(activeJob.id, 1, nextVerdict);
  };

  const downloadExport = async (format: "csv" | "xlsx") => {
    if (!activeJob) return;
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const blob = await api.exportDirectoryVerifyJob(activeJob.id, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `directory-verify-job-${activeJob.id}.${format}`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (error: unknown) {
      if (isGoogleScopeMissingError(error)) {
        setScopeError(error);
      }
      setMsg(error instanceof Error ? error.message : "Failed to export results.");
    } finally {
      setBusy(false);
    }
  };

  const summary = useMemo(() => {
    const json = activeJob?.summary_json || {};
    return {
      total: activeJob?.row_count || 0,
      exists: Number(json.exists || 0),
      does_not_exist: Number(json.does_not_exist || 0),
      ambiguous: Number(json.ambiguous || 0),
      invalid_input: Number(json.invalid_input || 0),
    };
  }, [activeJob]);

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Directory Verification</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Sync local directory, verify uploaded CSV/XLSX rows against local indexed users, and export results.
      </p>
      {msg && <div style={notice}>{msg}</div>}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      <section style={card}>
        <h3 style={{ marginTop: 0 }}>A. Sync panel</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <button onClick={handleSync} disabled={busy} style={btnPrimary}>
            {busy ? "Working…" : "Sync Directory"}
          </button>
          <button onClick={loadStats} disabled={busy} style={btnOutline}>Refresh Stats</button>
        </div>
        <div style={{ marginTop: 10, fontSize: 13, color: "#374151" }}>
          <div><b>Total synced users:</b> {stats?.total_directory_users ?? "—"}</div>
          <div><b>Last sync:</b> {stats?.latest_sync_job?.completed_at ? new Date(stats.latest_sync_job.completed_at).toLocaleString() : "—"}</div>
          <div><b>Last sync status:</b> {stats?.latest_sync_job?.status || "—"}</div>
          {stats?.running_sync_job ? (
            <div>
              <b>Sync in progress:</b> fetched {stats.running_sync_job.users_fetched_total} users across {stats.running_sync_job.pages_fetched} pages
            </div>
          ) : null}
        </div>
      </section>

      <section style={card}>
        <h3 style={{ marginTop: 0 }}>B. Upload panel + C. Column mapping</h3>
        <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
          <input
            type="file"
            accept=".csv,.tsv,.txt,.xlsx,.xlsm"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
          <button onClick={analyzeUpload} disabled={busy || !file} style={btnOutline}>
            Analyze Headers
          </button>
          <button onClick={runVerification} disabled={busy || !file || !mappingPreview} style={btnPrimary}>
            Run Verification
          </button>
        </div>
        {file ? <div style={{ marginTop: 8, fontSize: 12 }}>Selected file: {file.name}</div> : null}

        {mappingPreview ? (
          <div style={{ marginTop: 12, border: "1px solid #d1d5db", borderRadius: 8, padding: 10 }}>
            <div style={{ fontSize: 12, marginBottom: 8 }}>
              <b>Rows detected:</b> {mappingPreview.row_count}
            </div>
            {mappingPreview.available_sheets?.length > 0 ? (
              <div style={{ marginBottom: 8 }}>
                <label style={lbl}>Worksheet</label>
                <select
                  value={selectedSheet}
                  onChange={(event) => setSelectedSheet(event.target.value)}
                  style={input}
                >
                  {mappingPreview.available_sheets.map((sheet) => (
                    <option key={sheet} value={sheet}>{sheet}</option>
                  ))}
                </select>
              </div>
            ) : null}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8 }}>
              {CANONICAL_FIELDS.map((field) => (
                <div key={field.key}>
                  <label style={lbl}>{field.label}</label>
                  <select
                    value={mapping[field.key] || ""}
                    onChange={(event) => setMapping((prev) => ({ ...prev, [field.key]: event.target.value }))}
                    style={input}
                  >
                    <option value="">-- not mapped --</option>
                    {mappingPreview.headers.map((header) => (
                      <option key={header} value={header}>{header}</option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
          </div>
        ) : null}
      </section>

      <section style={card}>
        <h3 style={{ marginTop: 0 }}>D. Results panel</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap", marginBottom: 10 }}>
          <select value={activeJob?.id || ""} onChange={(e) => {
            const id = Number(e.target.value);
            const job = jobs.find((j) => j.id === id);
            if (job) {
              changeJob(job);
            }
          }} style={input}>
            <option value="">Select verification job</option>
            {jobs.map((job) => (
              <option key={job.id} value={job.id}>
                #{job.id} • {job.source_filename} • {job.status}
              </option>
            ))}
          </select>
          <select value={verdictFilter} onChange={(e) => applyVerdictFilter(e.target.value)} style={input}>
            <option value="">All verdicts</option>
            <option value="exists">exists</option>
            <option value="does_not_exist">does_not_exist</option>
            <option value="ambiguous">ambiguous</option>
            <option value="invalid_input">invalid_input</option>
          </select>
          <button onClick={() => activeJob && loadRows(activeJob.id, page, verdictFilter)} style={btnOutline}>Refresh Rows</button>
          <button onClick={() => downloadExport("csv")} disabled={!activeJob || busy} style={btnOutline}>Export CSV</button>
          <button onClick={() => downloadExport("xlsx")} disabled={!activeJob || busy} style={btnOutline}>Export XLSX</button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: 8, marginBottom: 10 }}>
          <Stat label="Total rows" value={summary.total} />
          <Stat label="Exists" value={summary.exists} tone="#047857" />
          <Stat label="Does not exist" value={summary.does_not_exist} tone="#991b1b" />
          <Stat label="Ambiguous" value={summary.ambiguous} tone="#92400e" />
          <Stat label="Invalid input" value={summary.invalid_input} tone="#4338ca" />
        </div>

        {loadingRows ? (
          <p>Loading rows…</p>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
            <thead>
              <tr style={{ background: "#f3f4f6" }}>
                <th style={th}>Row</th>
                <th style={th}>Input Name</th>
                <th style={th}>Roll No</th>
                <th style={th}>Phone</th>
                <th style={th}>Input Emails</th>
                <th style={th}>Matched Email</th>
                <th style={th}>Matched Name</th>
                <th style={th}>Match Basis</th>
                <th style={th}>Verdict</th>
                <th style={th}>Notes</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => {
                const input = row.input_json || {};
                const inputEmails = [input.official_email_issued, input.email_address, input.email_pmc]
                  .filter(Boolean)
                  .join(", ");
                return (
                  <tr key={row.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={td}>{row.row_no}</td>
                    <td style={td}>{input.name || "—"}</td>
                    <td style={td}>{input.roll_no || "—"}</td>
                    <td style={td}>{input.phone_number || "—"}</td>
                    <td style={td}>{inputEmails || "—"}</td>
                    <td style={td}>{row.matched_email || "—"}</td>
                    <td style={td}>{row.matched_name || "—"}</td>
                    <td style={td}>{row.match_basis || "—"}</td>
                    <td style={td}>{row.verdict}</td>
                    <td style={td}>{row.notes || "—"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
        {activeJob ? (
          <div style={{ marginTop: 8, display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: 12 }}>
            <span>Showing {(page - 1) * 25 + 1}-{Math.min(page * 25, totalRows)} of {totalRows}</span>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                onClick={() => loadRows(activeJob.id, Math.max(page - 1, 1), verdictFilter)}
                disabled={page <= 1}
                style={btnOutline}
              >
                Prev
              </button>
              <button
                onClick={() => loadRows(activeJob.id, page + 1, verdictFilter)}
                disabled={page * 25 >= totalRows}
                style={btnOutline}
              >
                Next
              </button>
            </div>
          </div>
        ) : null}
      </section>
    </div>
  );
}

function Stat({ label, value, tone = "#111827" }: { label: string; value: number; tone?: string }) {
  return (
    <div style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 10 }}>
      <div style={{ fontSize: 11, color: "#6b7280" }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color: tone }}>{value}</div>
    </div>
  );
}

const card: React.CSSProperties = {
  border: "1px solid #d1d5db",
  borderRadius: 10,
  padding: 14,
  background: "#fff",
  marginBottom: 14,
};

const lbl: React.CSSProperties = {
  display: "block",
  fontSize: 12,
  fontWeight: 600,
  marginBottom: 3,
};

const input: React.CSSProperties = {
  minWidth: 200,
  padding: "7px 10px",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  fontSize: 13,
};

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
  marginBottom: 10,
  padding: "8px 12px",
  background: "#f0f9ff",
  borderRadius: 6,
  fontSize: 13,
};

const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px" };
const td: React.CSSProperties = { padding: "8px 10px", verticalAlign: "top" };
