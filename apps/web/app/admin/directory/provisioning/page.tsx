"use client";

import { useEffect, useMemo, useState } from "react";
import { api } from "../../../../lib/api";

type RecordItem = {
  id: number;
  full_name: string;
  user_category: string;
  generated_email: string;
  target_org_unit_path: string;
  status: string;
  failure_reason: string;
  created_at: string;
};

type PreviewResult = {
  id: number;
  generated_email: string;
  target_org_unit_path: string;
  status: string;
};

const defaultSingle = {
  full_name: "",
  given_name: "",
  family_name: "",
  user_category: "student",
  source_identifier: "",
  department: "",
  program: "",
  batch: "",
  year: "",
  temp_password_policy: "change_on_first_login",
};

export default function DirectoryProvisioningPage() {
  const [tab, setTab] = useState<"single" | "bulk">("single");
  const [single, setSingle] = useState(defaultSingle);
  const [singlePreview, setSinglePreview] = useState<PreviewResult | null>(null);
  const [bulkText, setBulkText] = useState("full_name,user_category,source_identifier,department,program,batch,year\n");
  const [bulkPreview, setBulkPreview] = useState<{ records: PreviewResult[]; errors: { row: number; detail: string }[] } | null>(null);
  const [bulkApprovalId, setBulkApprovalId] = useState<number | null>(null);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");

  const loadRecords = async () => {
    try {
      const res = await api.listProvisioningRecords();
      setRecords(res || []);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to load provisioning records.");
    }
  };

  useEffect(() => {
    loadRecords();
  }, []);

  const parseBulkRows = useMemo(() => {
    const lines = bulkText
      .split("\n")
      .map((x) => x.trim())
      .filter(Boolean);
    if (lines.length <= 1) return [];
    const headers = lines[0].split(",").map((h) => h.trim());
    return lines.slice(1).map((line) => {
      const values = line.split(",").map((v) => v.trim());
      const obj: Record<string, string> = {};
      headers.forEach((h, i) => {
        obj[h] = values[i] || "";
      });
      return {
        full_name: obj.full_name || "",
        user_category: obj.user_category || "student",
        source_identifier: obj.source_identifier || "",
        department: obj.department || "",
        program: obj.program || "",
        batch: obj.batch || "",
        year: obj.year || "",
      };
    });
  }, [bulkText]);

  const previewSingle = async () => {
    setBusy(true);
    setMsg("");
    try {
      const record = await api.provisioningPreview(single);
      setSinglePreview(record);
      setMsg(`Preview ready: ${record.generated_email} -> ${record.target_org_unit_path}`);
      await loadRecords();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Single preview failed.");
    } finally {
      setBusy(false);
    }
  };

  const createSingle = async () => {
    if (!singlePreview) return;
    setBusy(true);
    setMsg("");
    try {
      const result = await api.provisioningCreate({ preview_record_id: singlePreview.id });
      setMsg(`Provisioning result: ${result.status} (${result.generated_email}).`);
      await loadRecords();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Single create failed.");
    } finally {
      setBusy(false);
    }
  };

  const previewBulk = async () => {
    setBusy(true);
    setMsg("");
    try {
      const res = await api.provisioningBulkPreview(parseBulkRows);
      setBulkPreview(res);
      setMsg(`Bulk preview complete: ${res.preview_count} valid, ${res.error_count} errors.`);
      await loadRecords();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Bulk preview failed.");
    } finally {
      setBusy(false);
    }
  };

  const createBulk = async () => {
    if (!bulkPreview || bulkPreview.records.length === 0) return;
    if (!bulkApprovalId) {
      setMsg("Request and obtain approval before bulk create.");
      return;
    }
    setBusy(true);
    setMsg("");
    try {
      const ids = bulkPreview.records.map((r) => r.id);
      const result = await api.provisioningBulkCreate(ids, bulkApprovalId);
      setMsg(`Bulk provisioning queued: ${result.record_count} records (task ${result.task_id}).`);
      await loadRecords();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Bulk create failed.");
    } finally {
      setBusy(false);
    }
  };

  const requestBulkApproval = async () => {
    if (!bulkPreview || bulkPreview.records.length === 0) return;
    setBusy(true);
    setMsg("");
    try {
      const ids = bulkPreview.records.map((r) => r.id);
      const approval = await api.createDirectoryApprovalRequest({
        action_type: "bulk_provisioning_create",
        target_type: "provisioning_batch",
        target_reference: `provisioning_records:${ids.join(",")}`,
        payload: { preview_record_ids: ids },
      });
      setBulkApprovalId(approval.id);
      setMsg(`Approval request #${approval.id} submitted for bulk provisioning.`);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to request bulk approval.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Create New IDs</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Preview-first account provisioning with generated email and dedicated OU placement.
      </p>
      {msg && <div style={notice}>{msg}</div>}

      <div style={{ display: "flex", gap: 6, marginBottom: 12 }}>
        <button onClick={() => setTab("single")} style={tab === "single" ? btnPrimary : btnOutline}>Single Create</button>
        <button onClick={() => setTab("bulk")} style={tab === "bulk" ? btnPrimary : btnOutline}>Bulk Create</button>
      </div>

      {tab === "single" ? (
        <div style={card}>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 8 }}>
            <Field label="Full name" value={single.full_name} onChange={(v) => setSingle({ ...single, full_name: v })} />
            <Field label="Given name" value={single.given_name} onChange={(v) => setSingle({ ...single, given_name: v })} />
            <Field label="Family name" value={single.family_name} onChange={(v) => setSingle({ ...single, family_name: v })} />
            <Field label="Identifier" value={single.source_identifier} onChange={(v) => setSingle({ ...single, source_identifier: v })} />
            <Field label="Department" value={single.department} onChange={(v) => setSingle({ ...single, department: v })} />
            <Field label="Program" value={single.program} onChange={(v) => setSingle({ ...single, program: v })} />
            <Field label="Batch" value={single.batch} onChange={(v) => setSingle({ ...single, batch: v })} />
            <Field label="Year" value={single.year} onChange={(v) => setSingle({ ...single, year: v })} />
            <div>
              <label style={lbl}>Category</label>
              <select value={single.user_category} onChange={(e) => setSingle({ ...single, user_category: e.target.value })} style={input}>
                <option value="student">student</option>
                <option value="faculty">faculty</option>
                <option value="staff">staff</option>
                <option value="other">other</option>
              </select>
            </div>
          </div>
          <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
            <button onClick={previewSingle} disabled={busy || !single.full_name} style={btnOutline}>
              Preview
            </button>
            <button onClick={createSingle} disabled={busy || !singlePreview} style={btnPrimary}>
              Create
            </button>
          </div>
          {singlePreview && (
            <div style={{ marginTop: 10, background: "#eff6ff", padding: 10, borderRadius: 8, fontSize: 13 }}>
              <div><b>Generated email:</b> {singlePreview.generated_email}</div>
              <div><b>Target OU:</b> {singlePreview.target_org_unit_path}</div>
              <div><b>Status:</b> {singlePreview.status}</div>
              <div style={{ marginTop: 6, color: "#1f2937" }}>
                Temporary password policy: change on first login (server-controlled).
              </div>
            </div>
          )}
        </div>
      ) : (
        <div style={card}>
          <p style={{ fontSize: 12, color: "#4b5563" }}>
            CSV columns: <code>full_name,user_category,source_identifier,department,program,batch,year</code>
          </p>
          <textarea
            value={bulkText}
            onChange={(e) => setBulkText(e.target.value)}
            rows={10}
            style={{ width: "100%", fontFamily: "monospace", border: "1px solid #d1d5db", borderRadius: 8, padding: 10, boxSizing: "border-box" }}
          />
          <div style={{ marginTop: 10, display: "flex", gap: 8 }}>
            <button onClick={previewBulk} disabled={busy || parseBulkRows.length === 0} style={btnOutline}>
              Bulk Preview
            </button>
            <button onClick={requestBulkApproval} disabled={busy || !bulkPreview || bulkPreview.records.length === 0} style={btnOutline}>
              Request Approval
            </button>
            <button onClick={createBulk} disabled={busy || !bulkPreview || bulkPreview.records.length === 0} style={btnPrimary}>
              Bulk Create
            </button>
          </div>
          {bulkPreview && (
            <div style={{ marginTop: 10, fontSize: 12 }}>
              <div><b>Preview records:</b> {bulkPreview.records.length}</div>
              <div><b>Errors:</b> {bulkPreview.errors.length}</div>
              <div><b>Approval request:</b> {bulkApprovalId ? `#${bulkApprovalId}` : "not requested"}</div>
              {bulkPreview.errors.length > 0 && (
                <ul>
                  {bulkPreview.errors.map((e) => (
                    <li key={e.row}>Row {e.row}: {e.detail}</li>
                  ))}
                </ul>
              )}
            </div>
          )}
        </div>
      )}

      <h3 style={{ marginTop: 22 }}>Recent provisioning records</h3>
      <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
        <thead>
          <tr style={{ background: "#f3f4f6" }}>
            <th style={th}>Email</th>
            <th style={th}>Category</th>
            <th style={th}>Target OU</th>
            <th style={th}>Status</th>
            <th style={th}>Created</th>
            <th style={th}>Failure</th>
          </tr>
        </thead>
        <tbody>
          {records.slice(0, 100).map((r) => (
            <tr key={r.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
              <td style={td}>{r.generated_email || r.full_name}</td>
              <td style={td}>{r.user_category}</td>
              <td style={td}>{r.target_org_unit_path || "—"}</td>
              <td style={td}>{r.status}</td>
              <td style={td}>{new Date(r.created_at).toLocaleString()}</td>
              <td style={td}>{r.failure_reason || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (v: string) => void }) {
  return (
    <div>
      <label style={lbl}>{label}</label>
      <input value={value} onChange={(e) => onChange(e.target.value)} style={input} />
    </div>
  );
}

const card: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 10, padding: 14, background: "#fff" };
const lbl: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, marginBottom: 3 };
const input: React.CSSProperties = { width: "100%", padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13, boxSizing: "border-box" };
const btnPrimary: React.CSSProperties = { padding: "8px 12px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" };
const btnOutline: React.CSSProperties = { padding: "8px 12px", background: "#fff", color: "#1f2937", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" };
const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: 12 };
const td: React.CSSProperties = { padding: "8px 10px" };
const notice: React.CSSProperties = { marginBottom: 10, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 };
