"use client";

import { useEffect, useState } from "react";
import GoogleScopePrompt from "../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../lib/api";

type Group = {
  id: number;
  external_id: string;
  email: string;
  display_name: string;
  metadata_json: Record<string, unknown>;
  synced_at: string | null;
};

type Member = { email: string; role: string; type: string };

export default function GroupsPage() {
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [selectedGroup, setSelectedGroup] = useState<Group | null>(null);
  const [members, setMembers] = useState<Member[]>([]);
  const [membersLoading, setMembersLoading] = useState(false);
  const [msg, setMsg] = useState("");
  const [msgType, setMsgType] = useState<"info" | "error">("info");
  const [scopeError, setScopeError] = useState<ApiError | null>(null);

  // Add / remove member form
  const [memberEmail, setMemberEmail] = useState("");
  const [memberAction, setMemberAction] = useState<"add" | "remove">("add");
  const [memberBusy, setMemberBusy] = useState(false);

  const flash = (text: string, type: "info" | "error" = "info") => { setMsg(text); setMsgType(type); };

  const load = () => {
    setLoading(true);
    setScopeError(null);
    api.listGroups()
      .then((d) => setGroups(d))
      .catch((err: unknown) => {
        if (isGoogleScopeMissingError(err)) {
          setScopeError(err);
          flash("Additional Google permission is required to access group operations.", "error");
          return;
        }
        flash("Failed to load groups", "error");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSync = async () => {
    setSyncing(true);
    flash("");
    try {
      setScopeError(null);
      const res = await api.syncGroups();
      flash(`Synced: ${res.synced} groups (${res.created} new, ${res.updated} updated)`);
      load();
    } catch (err: unknown) {
      if (isGoogleScopeMissingError(err)) {
        setScopeError(err);
        flash("Additional Google permission is required to sync groups.", "error");
      } else {
        flash("Sync failed.", "error");
      }
    } finally {
      setSyncing(false);
    }
  };

  const handleViewMembers = async (g: Group) => {
    setSelectedGroup(g);
    setMembersLoading(true);
    setMembers([]);
    setMemberEmail("");
    try {
      const res = await api.groupMembers(g.email);
      setMembers(res.members || []);
    } catch {
      setMembers([]);
    } finally {
      setMembersLoading(false);
    }
  };

  const handleMemberAction = async () => {
    if (!selectedGroup || !memberEmail.trim()) return;
    setMemberBusy(true);
    try {
      if (memberAction === "add") {
        await api.addMemberToGroup(selectedGroup.email, memberEmail.trim());
        flash(`✅ Added ${memberEmail} to ${selectedGroup.display_name}`);
      } else {
        await api.removeMemberFromGroup(selectedGroup.email, memberEmail.trim());
        flash(`✅ Removed ${memberEmail} from ${selectedGroup.display_name}`);
      }
      setMemberEmail("");
      // Refresh member list
      const res = await api.groupMembers(selectedGroup.email);
      setMembers(res.members || []);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Operation failed";
      flash(msg, "error");
    } finally {
      setMemberBusy(false);
    }
  };

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Google Groups</h1>
        <button
          onClick={handleSync}
          disabled={syncing}
          style={{ padding: "8px 18px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
        >
          {syncing ? "Syncing…" : "Sync from Google"}
        </button>
      </div>
      {msg && (
        <div style={{ marginBottom: 12, padding: "8px 12px", background: msgType === "error" ? "#fef2f2" : "#f0f9ff", color: msgType === "error" ? "#b91c1c" : "#1e40af", borderRadius: 6, fontSize: 13 }}>
          {msg}
        </div>
      )}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      {loading ? (
        <p>Loading…</p>
      ) : groups.length === 0 ? (
        <p style={{ color: "#666" }}>No groups synced yet. Click "Sync from Google".</p>
      ) : (
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr style={{ background: "#f3f4f6" }}>
              <th style={th}>Name</th>
              <th style={th}>Email</th>
              <th style={th}>Members</th>
              <th style={th}>Last Synced</th>
              <th style={th}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {groups.map((g) => (
              <tr key={g.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                <td style={td}>{g.display_name}</td>
                <td style={td}><code>{g.email}</code></td>
                <td style={td}>{String(g.metadata_json?.directMembersCount ?? "—")}</td>
                <td style={td}>{g.synced_at ? new Date(g.synced_at).toLocaleString() : "—"}</td>
                <td style={td}>
                  <button
                    onClick={() => handleViewMembers(g)}
                    style={{ fontSize: 12, padding: "3px 10px", background: selectedGroup?.id === g.id ? "#2563eb" : "#e0e7ff", color: selectedGroup?.id === g.id ? "#fff" : "#1e40af", border: "none", borderRadius: 4, cursor: "pointer" }}
                  >
                    {selectedGroup?.id === g.id ? "▶ Viewing" : "Members"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {selectedGroup && (
        <div style={{ marginTop: 24, padding: 20, border: "1px solid #d1d5db", borderRadius: 8, background: "#fff" }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
            <h3 style={{ margin: 0 }}>👥 {selectedGroup.display_name}</h3>
            <button onClick={() => setSelectedGroup(null)} style={{ background: "none", border: "none", cursor: "pointer", fontSize: 18, color: "#666" }}>×</button>
          </div>

          {/* Add / Remove member form */}
          <div style={{ display: "flex", gap: 8, marginBottom: 16, alignItems: "center", flexWrap: "wrap" }}>
            <select
              value={memberAction}
              onChange={(e) => setMemberAction(e.target.value as "add" | "remove")}
              style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13 }}
            >
              <option value="add">Add member</option>
              <option value="remove">Remove member</option>
            </select>
            <input
              type="email"
              placeholder="user@domain.com"
              value={memberEmail}
              onChange={(e) => setMemberEmail(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleMemberAction()}
              style={{ padding: "6px 10px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13, minWidth: 240 }}
            />
            <button
              onClick={handleMemberAction}
              disabled={memberBusy || !memberEmail.trim()}
              style={{ padding: "6px 14px", background: memberAction === "add" ? "#16a34a" : "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13, fontWeight: 600 }}
            >
              {memberBusy ? "…" : memberAction === "add" ? "Add" : "Remove"}
            </button>
          </div>

          {/* Member list */}
          {membersLoading ? (
            <p>Loading members…</p>
          ) : members.length === 0 ? (
            <p style={{ color: "#666", fontSize: 13 }}>No members found.</p>
          ) : (
            <ul style={{ listStyle: "none", padding: 0, margin: 0 }}>
              {members.map((m) => (
                <li key={m.email} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid #f0f0f0", fontSize: 13 }}>
                  <span>{m.email} <span style={{ color: "#888", fontSize: 11 }}>({m.role || m.type})</span></span>
                  <button
                    onClick={() => { setMemberEmail(m.email); setMemberAction("remove"); }}
                    style={{ fontSize: 11, padding: "2px 8px", background: "#fee2e2", color: "#b91c1c", border: "none", borderRadius: 4, cursor: "pointer" }}
                  >
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 12px", fontWeight: 600, fontSize: 12, color: "#374151" };
const td: React.CSSProperties = { padding: "8px 12px", verticalAlign: "middle" };
