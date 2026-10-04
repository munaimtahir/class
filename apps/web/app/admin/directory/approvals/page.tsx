"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "../../../../lib/api";

type ApprovalRequest = {
  id: number;
  action_type: string;
  target_type: string;
  target_reference: string;
  payload: Record<string, unknown>;
  requested_by_email: string | null;
  requested_at: string;
  status: string;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  review_notes: string;
  execution_status: string;
  execution_message: string;
  linked_change_job: number | null;
  linked_provisioning_record: number | null;
  created_at: string;
};

export default function DirectoryApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<"pending" | "history">("pending");
  const [msg, setMsg] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);

  const load = async () => {
    setLoading(true);
    setMsg("");
    try {
      const rows = await api.listDirectoryApprovalRequests();
      setApprovals(rows || []);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to load approval requests.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const pending = useMemo(() => approvals.filter((a) => a.status === "pending"), [approvals]);
  const history = useMemo(() => approvals.filter((a) => a.status !== "pending"), [approvals]);
  const rows = tab === "pending" ? pending : history;

  const act = async (id: number, action: "approve" | "reject" | "cancel") => {
    setBusyId(id);
    setMsg("");
    try {
      if (action === "approve") await api.approveDirectoryApprovalRequest(id, "");
      if (action === "reject") await api.rejectDirectoryApprovalRequest(id, "");
      if (action === "cancel") await api.cancelDirectoryApprovalRequest(id, "");
      await load();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : `Failed to ${action} request.`);
    } finally {
      setBusyId(null);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Approval Requests</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Separate approval review for restricted actions before execution.
      </p>
      {msg && <div style={notice}>{msg}</div>}

      <div style={{ display: "flex", gap: 8, marginBottom: 12 }}>
        <button onClick={() => setTab("pending")} style={tab === "pending" ? btnPrimary : btnOutline}>
          Pending ({pending.length})
        </button>
        <button onClick={() => setTab("history")} style={tab === "history" ? btnPrimary : btnOutline}>
          History ({history.length})
        </button>
        <button onClick={load} style={btnOutline}>Refresh</button>
      </div>

      {loading ? (
        <p>Loading…</p>
      ) : rows.length === 0 ? (
        <p style={{ color: "#6b7280" }}>No approval requests in this view.</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th style={th}>ID</th>
              <th style={th}>Action</th>
              <th style={th}>Target</th>
              <th style={th}>Requester</th>
              <th style={th}>Status</th>
              <th style={th}>Execution</th>
              <th style={th}>Review</th>
              <th style={th}>Details</th>
              <th style={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} style={{ borderBottom: "1px solid #e5e7eb", verticalAlign: "top" }}>
                <td style={td}>#{r.id}</td>
                <td style={td}>{r.action_type}</td>
                <td style={td}>{r.target_reference}</td>
                <td style={td}>{r.requested_by_email || "—"}</td>
                <td style={td}>{r.status}</td>
                <td style={td}>{r.execution_status}</td>
                <td style={td}>
                  {r.reviewed_by_email || "—"}
                  {r.reviewed_at ? <div style={{ fontSize: 11 }}>{new Date(r.reviewed_at).toLocaleString()}</div> : null}
                  {r.review_notes ? <div style={{ fontSize: 11, marginTop: 3 }}>{r.review_notes}</div> : null}
                </td>
                <td style={td}>
                  <div style={{ fontSize: 11, color: "#374151" }}>
                    {r.linked_change_job ? <div>Job #{r.linked_change_job}</div> : null}
                    {r.linked_provisioning_record ? <div>Record #{r.linked_provisioning_record}</div> : null}
                    {r.execution_message ? <div>{r.execution_message}</div> : null}
                  </div>
                  <details>
                    <summary style={{ cursor: "pointer", color: "#1d4ed8", fontSize: 12 }}>Payload</summary>
                    <pre style={{ marginTop: 6, maxWidth: 260, whiteSpace: "pre-wrap" }}>{JSON.stringify(r.payload || {}, null, 2)}</pre>
                  </details>
                </td>
                <td style={td}>
                  {r.status === "pending" ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                      <button disabled={busyId === r.id} onClick={() => act(r.id, "approve")} style={miniPrimary}>
                        Approve
                      </button>
                      <button disabled={busyId === r.id} onClick={() => act(r.id, "reject")} style={miniDanger}>
                        Reject
                      </button>
                      <button disabled={busyId === r.id} onClick={() => act(r.id, "cancel")} style={miniOutline}>
                        Cancel
                      </button>
                    </div>
                  ) : (
                    "—"
                  )}
                </td>
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
const miniPrimary: React.CSSProperties = { fontSize: 11, padding: "4px 8px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 5, cursor: "pointer" };
const miniDanger: React.CSSProperties = { fontSize: 11, padding: "4px 8px", background: "#dc2626", color: "#fff", border: "none", borderRadius: 5, cursor: "pointer" };
const miniOutline: React.CSSProperties = { fontSize: 11, padding: "4px 8px", background: "#fff", color: "#374151", border: "1px solid #d1d5db", borderRadius: 5, cursor: "pointer" };
const notice: React.CSSProperties = { marginBottom: 10, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 };
