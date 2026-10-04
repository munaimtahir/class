"use client";

import { useEffect, useMemo, useState } from "react";
import GoogleScopePrompt from "../../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../../lib/api";

type DirectoryUser = {
  id: number;
  primary_email: string;
  full_name: string;
  user_category: string;
  org_unit_path: string;
  expected_org_unit_path: string;
  expected_email_valid: boolean | null;
  external_identifier: string;
  suspended: boolean;
  archived: boolean;
  last_synced_at: string | null;
};

type DirectoryIssue = {
  id: number;
  directory_user: number | null;
  severity: "critical" | "warning" | "info";
  status: string;
  issue_type: string;
};

const PAGE_SIZE = 20;

export default function DirectoryUsersPage() {
  const [users, setUsers] = useState<DirectoryUser[]>([]);
  const [issues, setIssues] = useState<DirectoryIssue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [q, setQ] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [msg, setMsg] = useState("");
  const [scopeError, setScopeError] = useState<ApiError | null>(null);

  const load = async () => {
    setLoading(true);
    setMsg("");
    try {
      setScopeError(null);
      const [u, i] = await Promise.all([
        api.listDirectoryUsers({
          ...(q ? { q } : {}),
          ...(category ? { category } : {}),
        }),
        api.listDirectoryIssues({}),
      ]);
      setUsers(u || []);
      setIssues(i || []);
      setPage(1);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
      }
      setMsg(e instanceof Error ? e.message : "Failed to load users.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const issueMap = useMemo(() => {
    const map: Record<number, DirectoryIssue[]> = {};
    for (const issue of issues) {
      if (!issue.directory_user) continue;
      map[issue.directory_user] = map[issue.directory_user] || [];
      map[issue.directory_user].push(issue);
    }
    return map;
  }, [issues]);

  const pagedUsers = useMemo(() => {
    const start = (page - 1) * PAGE_SIZE;
    return users.slice(start, start + PAGE_SIZE);
  }, [users, page]);

  const selected = users.find((u) => u.id === selectedId) || null;
  const selectedIssues = selected ? issueMap[selected.id] || [] : [];

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>Directory Users</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Search synced users by email/name/identifier and review expected vs actual OU/email validity.
      </p>
      {msg && <div style={notice}>{msg}</div>}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 12 }}>
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search email, name, identifier"
          style={input}
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} style={input}>
          <option value="">All categories</option>
          <option value="student">student</option>
          <option value="faculty">faculty</option>
          <option value="staff">staff</option>
          <option value="other">other</option>
        </select>
        <button onClick={load} style={btnPrimary}>
          Apply
        </button>
      </div>

      <div style={{ display: "flex", gap: 18, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 680px" }}>
          {loading ? (
            <p>Loading…</p>
          ) : (
            <>
              <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
                <thead>
                  <tr style={{ background: "#f3f4f6" }}>
                    <th style={th}>Email</th>
                    <th style={th}>Category</th>
                    <th style={th}>Actual OU</th>
                    <th style={th}>Expected OU</th>
                    <th style={th}>Email Rule</th>
                    <th style={th}>Issues</th>
                  </tr>
                </thead>
                <tbody>
                  {pagedUsers.map((u) => {
                    const userIssues = issueMap[u.id] || [];
                    return (
                      <tr
                        key={u.id}
                        onClick={() => setSelectedId(u.id)}
                        style={{
                          borderBottom: "1px solid #e5e7eb",
                          cursor: "pointer",
                          background: selectedId === u.id ? "#eff6ff" : undefined,
                        }}
                      >
                        <td style={td}>{u.primary_email}</td>
                        <td style={td}>{u.user_category}</td>
                        <td style={td}>{u.org_unit_path || "—"}</td>
                        <td style={td}>{u.expected_org_unit_path || "—"}</td>
                        <td style={td}>{u.expected_email_valid === null ? "N/A" : u.expected_email_valid ? "valid" : "invalid"}</td>
                        <td style={td}>{userIssues.length}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <div style={{ display: "flex", justifyContent: "space-between", marginTop: 10, fontSize: 12 }}>
                <span>
                  Showing {(page - 1) * PAGE_SIZE + 1}-{Math.min(page * PAGE_SIZE, users.length)} of {users.length}
                </span>
                <div style={{ display: "flex", gap: 6 }}>
                  <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)} style={btnOutline}>
                    Prev
                  </button>
                  <button
                    disabled={page * PAGE_SIZE >= users.length}
                    onClick={() => setPage((p) => p + 1)}
                    style={btnOutline}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>

        <div style={{ flex: "0 0 340px", border: "1px solid #d1d5db", borderRadius: 8, padding: 14 }}>
          <h3 style={{ marginTop: 0, fontSize: 15 }}>User Details</h3>
          {!selected ? (
            <p style={{ color: "#6b7280", fontSize: 13 }}>Select a user to inspect details and issue badges.</p>
          ) : (
            <>
              <div style={{ fontSize: 13, marginBottom: 8 }}>
                <b>{selected.full_name || selected.primary_email}</b>
                <div>{selected.primary_email}</div>
              </div>
              <div style={{ fontSize: 12, color: "#374151", marginBottom: 8 }}>
                <div><b>Category:</b> {selected.user_category}</div>
                <div><b>External ID:</b> {selected.external_identifier || "—"}</div>
                <div><b>Actual OU:</b> {selected.org_unit_path || "—"}</div>
                <div><b>Expected OU:</b> {selected.expected_org_unit_path || "—"}</div>
                <div><b>Email pattern:</b> {selected.expected_email_valid === null ? "N/A" : selected.expected_email_valid ? "valid" : "invalid"}</div>
                <div><b>Status:</b> {selected.suspended ? "suspended" : "active"}{selected.archived ? " / archived" : ""}</div>
                <div><b>Last synced:</b> {selected.last_synced_at ? new Date(selected.last_synced_at).toLocaleString() : "—"}</div>
              </div>
              <h4 style={{ marginBottom: 6, fontSize: 13 }}>Issue badges</h4>
              {selectedIssues.length === 0 ? (
                <p style={{ color: "#6b7280", fontSize: 12 }}>No issues linked.</p>
              ) : (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                  {selectedIssues.map((issue) => (
                    <span key={issue.id} style={{ ...pill, ...severityStyle(issue.severity) }}>
                      {issue.issue_type}
                    </span>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

function severityStyle(sev: "critical" | "warning" | "info") {
  if (sev === "critical") return { background: "#fee2e2", color: "#b91c1c" };
  if (sev === "warning") return { background: "#fef3c7", color: "#92400e" };
  return { background: "#dbeafe", color: "#1d4ed8" };
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 10px", fontSize: 12 };
const td: React.CSSProperties = { padding: "8px 10px" };
const input: React.CSSProperties = {
  padding: "7px 10px",
  border: "1px solid #d1d5db",
  borderRadius: 6,
  fontSize: 13,
};
const btnPrimary: React.CSSProperties = {
  padding: "7px 12px",
  background: "#1d4ed8",
  color: "#fff",
  border: "none",
  borderRadius: 6,
  cursor: "pointer",
};
const btnOutline: React.CSSProperties = {
  padding: "6px 10px",
  border: "1px solid #d1d5db",
  background: "#fff",
  borderRadius: 6,
  cursor: "pointer",
  fontSize: 12,
};
const notice: React.CSSProperties = {
  marginBottom: 10,
  padding: "8px 12px",
  background: "#f0f9ff",
  borderRadius: 6,
  fontSize: 13,
};
const pill: React.CSSProperties = {
  fontSize: 11,
  padding: "3px 8px",
  borderRadius: 9999,
  fontWeight: 600,
};
