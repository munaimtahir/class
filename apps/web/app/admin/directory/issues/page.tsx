"use client";

import { useEffect, useMemo, useState } from "react";
import GoogleScopePrompt from "../../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../../lib/api";

type Issue = {
  id: number;
  directory_user: number | null;
  directory_user_email: string | null;
  issue_type: string;
  severity: "critical" | "warning" | "info";
  actual_value: string;
  expected_value: string;
  suggested_action: string;
  status: string;
  detected_at: string;
  failure_reason?: string;
};

type PreviewItem = {
  id: number;
  issue: number | null;
  action: string;
  before_value: string;
  after_value: string;
  status: string;
  result_json?: Record<string, unknown>;
  error_text?: string;
};

type PreviewJob = {
  id: number;
  scope_type: string;
  status: string;
  item_count: number;
  preview_summary: Record<string, unknown>;
  execution_summary?: Record<string, unknown>;
  items?: PreviewItem[];
};

export default function DirectoryIssuesPage() {
  const [issues, setIssues] = useState<Issue[]>([]);
  const [statusFilter, setStatusFilter] = useState("");
  const [severityFilter, setSeverityFilter] = useState("");
  const [issueTypeFilter, setIssueTypeFilter] = useState("");
  const [suggestedActionFilter, setSuggestedActionFilter] = useState("");
  const [searchFilter, setSearchFilter] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [previewJob, setPreviewJob] = useState<PreviewJob | null>(null);
  const [executionJob, setExecutionJob] = useState<PreviewJob | null>(null);
  const [approvalRequestId, setApprovalRequestId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [scopeError, setScopeError] = useState<ApiError | null>(null);

  const load = async () => {
    setLoading(true);
    setMsg("");
    try {
      setScopeError(null);
      const res = await api.listDirectoryIssues({
        ...(statusFilter ? { status: statusFilter } : {}),
        ...(severityFilter ? { severity: severityFilter } : {}),
        ...(issueTypeFilter ? { issue_type: issueTypeFilter } : {}),
        ...(suggestedActionFilter ? { suggested_action: suggestedActionFilter } : {}),
        ...(searchFilter.trim() ? { q: searchFilter.trim() } : {}),
      });
      setIssues(res || []);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Failed to load issues.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const selectedIds = useMemo(() => Array.from(selected), [selected]);
  const previewItemByIssue = useMemo(() => {
    const map: Record<number, PreviewItem> = {};
    for (const item of previewJob?.items || []) {
      if (item.issue) map[item.issue] = item;
    }
    return map;
  }, [previewJob]);
  const executionItemByIssue = useMemo(() => {
    const map: Record<number, PreviewItem> = {};
    for (const item of executionJob?.items || []) {
      if (item.issue) map[item.issue] = item;
    }
    return map;
  }, [executionJob]);

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const applyAction = async (id: number, action: "approve" | "reject" | "exception") => {
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      if (action === "approve") await api.approveDirectoryIssue(id);
      if (action === "reject") await api.rejectDirectoryIssue(id);
      if (action === "exception") await api.markDirectoryIssueException(id);
      await load();
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Issue action failed.");
    } finally {
      setBusy(false);
    }
  };

  const bulkApprove = async () => {
    if (selectedIds.length === 0) return;
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      await api.bulkApproveDirectoryIssues(selectedIds);
      setSelected(new Set());
      await load();
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Bulk approve failed.");
    } finally {
      setBusy(false);
    }
  };

  const runScan = async () => {
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const res = await api.scanDirectoryIssues({});
      setMsg(`Scan created ${res.issues_created} issues from ${res.users_scanned} users.`);
      await load();
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Scan failed.");
    } finally {
      setBusy(false);
    }
  };

  const previewFixes = async () => {
    if (selectedIds.length === 0) return;
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const job = await api.previewDirectoryChangeJob({
        job_type: "ou_correction",
        scope_type: selectedIds.length > 1 ? "bulk" : "issue_selection",
        issue_ids: selectedIds,
      });
      setPreviewJob(job);
      setExecutionJob(null);
      setApprovalRequestId(null);
      setMsg(`Preview job #${job.id} created with ${job.item_count} items.`);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Preview failed.");
    } finally {
      setBusy(false);
    }
  };

  const executeFixes = async () => {
    if (!previewJob) return;
    if (previewJob.scope_type === "bulk" && !approvalRequestId) {
      setMsg("Request and obtain approval before executing bulk fixes.");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const result = await api.executeDirectoryChangeJob({
        preview_job_id: previewJob.id,
        dry_run: false,
        ...(approvalRequestId ? { approval_request_id: approvalRequestId } : {}),
      });
      setExecutionJob(result);
      setMsg(`Execution job #${result.id} status: ${result.status}.`);
      await load();
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Execution failed.");
    } finally {
      setBusy(false);
    }
  };

  const requestApproval = async () => {
    if (!previewJob) return;
    setBusy(true);
    setMsg("");
    try {
      setScopeError(null);
      const approval = await api.createDirectoryApprovalRequest({
        action_type: "bulk_change_job_execute",
        target_type: "change_job",
        target_reference: `change_job:${previewJob.id}`,
        payload: { preview_job_id: previewJob.id },
        linked_change_job_id: previewJob.id,
      });
      setApprovalRequestId(approval.id);
      setMsg(`Approval request #${approval.id} submitted for preview job #${previewJob.id}.`);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Failed to request approval.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Inconsistency Review</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Review operational mismatches, identify root-cause patterns, and inspect a clear fix plan before previewing.
        Preview artifacts show before/after values so execution stays controlled and auditable.
      </p>
      {msg && <div style={notice}>{msg}</div>}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      <div style={{ display: "flex", gap: 8, marginBottom: 12, flexWrap: "wrap" }}>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={input}>
          <option value="">All statuses</option>
          <option value="detected">detected</option>
          <option value="approved">approved</option>
          <option value="rejected">rejected</option>
          <option value="exception_marked">exception_marked</option>
          <option value="applied">applied</option>
          <option value="failed">failed</option>
        </select>
        <select value={severityFilter} onChange={(e) => setSeverityFilter(e.target.value)} style={input}>
          <option value="">All severities</option>
          <option value="critical">critical</option>
          <option value="warning">warning</option>
          <option value="info">info</option>
        </select>
        <select value={issueTypeFilter} onChange={(e) => setIssueTypeFilter(e.target.value)} style={input}>
          <option value="">All issue types</option>
          {ISSUE_TYPE_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <select value={suggestedActionFilter} onChange={(e) => setSuggestedActionFilter(e.target.value)} style={input}>
          <option value="">All suggested actions</option>
          {SUGGESTED_ACTION_OPTIONS.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <input
          value={searchFilter}
          onChange={(e) => setSearchFilter(e.target.value)}
          placeholder="Search user/type/action/value"
          style={{ ...input, minWidth: 220 }}
        />
        <button onClick={load} style={btnOutline}>Apply Filters</button>
        <button onClick={runScan} disabled={busy} style={btnPrimary}>Re-scan</button>
      </div>

      <div style={{ display: "flex", gap: 8, marginBottom: 10, flexWrap: "wrap" }}>
        <button onClick={bulkApprove} disabled={busy || selectedIds.length === 0} style={btnOutline}>
          Bulk Approve ({selectedIds.length})
        </button>
        <button onClick={previewFixes} disabled={busy || selectedIds.length === 0} style={btnPrimary}>
          Preview Suggested Fixes
        </button>
        <button onClick={requestApproval} disabled={busy || !previewJob || previewJob.scope_type !== "bulk"} style={btnOutline}>
          Request Approval
        </button>
        <button onClick={executeFixes} disabled={busy || !previewJob} style={dangerBtn}>
          Execute Approved Preview
        </button>
      </div>

      {previewJob && (
        <div style={{ marginBottom: 10, border: "1px solid #dbeafe", borderRadius: 8, padding: 10, background: "#eff6ff", fontSize: 13 }}>
          Preview job #{previewJob.id} ready. Dry-run artifact created before mutation execution.
          {previewJob.scope_type === "bulk" ? (
            <div style={{ marginTop: 4 }}><b>Approval request:</b> {approvalRequestId ? `#${approvalRequestId}` : "not requested"}</div>
          ) : null}
        </div>
      )}

      {loading ? (
        <p>Loading…</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th style={th}></th>
              <th style={th}>Severity</th>
              <th style={th}>Type</th>
              <th style={th}>User</th>
              <th style={th}>Actual</th>
              <th style={th}>Expected</th>
              <th style={th}>Suggested</th>
              <th style={th}>Fix Plan (Before Preview)</th>
              <th style={th}>Preview / Result</th>
              <th style={th}>Status</th>
              <th style={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {issues.map((issue) => (
              <tr key={issue.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={td}>
                  <input
                    type="checkbox"
                    checked={selected.has(issue.id)}
                    onChange={() => toggle(issue.id)}
                    aria-label={`Select issue ${issue.id}`}
                  />
                </td>
                <td style={td}>
                  <span style={{ ...pill, ...severityStyle(issue.severity) }}>{issue.severity}</span>
                </td>
                <td style={td}>{issue.issue_type}</td>
                <td style={td}>{issue.directory_user_email || "—"}</td>
                <td style={td}>{issue.actual_value || "—"}</td>
                <td style={td}>{issue.expected_value || "—"}</td>
                <td style={td}>{issue.suggested_action || "—"}</td>
                <td style={td}>{describeFixPlan(issue)}</td>
                <td style={td}>
                  {renderPreviewOrResult(issue, previewItemByIssue[issue.id], executionItemByIssue[issue.id], previewJob, executionJob)}
                </td>
                <td style={td}>{issue.status}</td>
                <td style={td}>
                  <div style={{ display: "flex", gap: 6 }}>
                    <button onClick={() => applyAction(issue.id, "approve")} disabled={busy} style={miniBtn}>Approve</button>
                    <button onClick={() => applyAction(issue.id, "reject")} disabled={busy} style={miniBtn}>Reject</button>
                    <button onClick={() => applyAction(issue.id, "exception")} disabled={busy} style={miniBtn}>
                      Exception
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

function severityStyle(sev: "critical" | "warning" | "info") {
  if (sev === "critical") return { background: "#fee2e2", color: "#b91c1c" };
  if (sev === "warning") return { background: "#fef3c7", color: "#92400e" };
  return { background: "#dbeafe", color: "#1d4ed8" };
}

function describeFixPlan(issue: Issue) {
  if (issue.suggested_action === "move_ou") {
    return `Move user org unit from "${issue.actual_value || "unknown"}" to "${issue.expected_value || "expected path"}".`;
  }
  if (issue.suggested_action === "update_identifier") {
    return "Update missing/incorrect identifier fields before retrying automated checks.";
  }
  if (issue.suggested_action === "review_template" || issue.suggested_action === "review_email_template") {
    return "Review and correct template rules, then re-scan to regenerate expected values.";
  }
  if (issue.suggested_action === "manual_review") {
    return "Manually validate this record and choose approve/reject/exception based on policy.";
  }
  return issue.suggested_action ? `Apply action: ${issue.suggested_action}.` : "No automated fix suggestion is available.";
}

function renderPreviewOrResult(
  issue: Issue,
  previewItem: PreviewItem | undefined,
  executionItem: PreviewItem | undefined,
  previewJob: PreviewJob | null,
  executionJob: PreviewJob | null,
) {
  if (executionItem) {
    return (
      <div style={{ fontSize: 12 }}>
        <div><b>Executed:</b> {executionItem.status}</div>
        <div>{executionItem.before_value || "—"} → {executionItem.after_value || "—"}</div>
        {executionItem.error_text ? <div style={{ color: "#b91c1c" }}>{executionItem.error_text}</div> : null}
      </div>
    );
  }
  if (previewItem) {
    return (
      <div style={{ fontSize: 12 }}>
        <div><b>Preview:</b> {previewItem.status}</div>
        <div>{previewItem.before_value || "—"} → {previewItem.after_value || "—"}</div>
      </div>
    );
  }
  if (executionJob) {
    return <span style={{ color: "#6b7280" }}>No execution artifact for this issue.</span>;
  }
  if (previewJob) {
    return <span style={{ color: "#6b7280" }}>No preview item generated for this issue.</span>;
  }
  if (issue.failure_reason) {
    return <span style={{ color: "#b91c1c" }}>{issue.failure_reason}</span>;
  }
  return <span style={{ color: "#6b7280" }}>Run preview to inspect before/after output.</span>;
}

const ISSUE_TYPE_OPTIONS = [
  "invalid_org_unit",
  "invalid_email_pattern",
  "missing_required_identifier",
  "likely_duplicate_conflict",
  "user_category_mismatch",
  "template_resolution_failure",
];

const SUGGESTED_ACTION_OPTIONS = [
  "move_ou",
  "manual_review",
  "review_template",
  "review_email_template",
  "update_identifier",
  "unsupported",
];

const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: 12 };
const td: React.CSSProperties = { padding: "8px 10px", verticalAlign: "top" };
const input: React.CSSProperties = { padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13 };
const btnPrimary: React.CSSProperties = { padding: "7px 12px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" };
const btnOutline: React.CSSProperties = { padding: "7px 12px", background: "#fff", color: "#1f2937", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" };
const dangerBtn: React.CSSProperties = { padding: "7px 12px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" };
const miniBtn: React.CSSProperties = { fontSize: 11, padding: "3px 8px", borderRadius: 4, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer" };
const pill: React.CSSProperties = { fontSize: 11, padding: "2px 7px", borderRadius: 9999, fontWeight: 700 };
const notice: React.CSSProperties = { marginBottom: 10, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 };
