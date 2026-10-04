"use client";

import { useEffect, useState } from "react";
import { api } from "../../../lib/api";

type Bundle = {
  id: number;
  name: string;
  role_type: string;
  groups_json: string[];
  classroom_courses_json: string[];
  description: string | null;
  active: boolean;
  created_by_email: string | null;
  created_at: string;
};

const emptyForm = {
  name: "",
  role_type: "student",
  groups_json: "",
  classroom_courses_json: "",
  description: "",
  active: true,
};

export default function BundlesPage() {
  const [bundles, setBundles] = useState<Bundle[]>([]);
  const [loading, setLoading] = useState(true);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  const load = () => {
    setLoading(true);
    api.listBundles().then(setBundles).catch(() => setMsg("Failed to load bundles.")).finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setMsg("");
    const payload = {
      name: form.name,
      role_type: form.role_type,
      groups_json: form.groups_json.split(",").map((s) => s.trim()).filter(Boolean),
      classroom_courses_json: form.classroom_courses_json.split(",").map((s) => s.trim()).filter(Boolean),
      description: form.description || null,
      active: form.active,
    };
    try {
      if (editingId) {
        await api.updateBundle(editingId, payload);
        setMsg("Bundle updated.");
      } else {
        await api.createBundle(payload);
        setMsg("Bundle created.");
      }
      setForm(emptyForm);
      setEditingId(null);
      load();
    } catch {
      setMsg("Save failed.");
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = (b: Bundle) => {
    setEditingId(b.id);
    setForm({
      name: b.name,
      role_type: b.role_type,
      groups_json: b.groups_json.join(", "),
      classroom_courses_json: b.classroom_courses_json.join(", "),
      description: b.description || "",
      active: b.active,
    });
  };

  const handleDelete = async (id: number) => {
    if (!confirm("Delete this bundle?")) return;
    try {
      await api.deleteBundle(id);
      load();
    } catch {
      setMsg("Delete failed.");
    }
  };

  return (
    <div>
      <h1>Onboarding Bundles</h1>
      {msg && <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 }}>{msg}</div>}

      <div style={{ display: "flex", gap: 32, flexWrap: "wrap" }}>
        <div style={{ flex: "1 1 500px" }}>
          {loading ? <p>Loading…</p> : bundles.length === 0 ? (
            <p style={{ color: "#666" }}>No bundles yet.</p>
          ) : (
            bundles.map((b) => (
              <div key={b.id} style={{ border: "1px solid #e5e7eb", borderRadius: 8, padding: 16, marginBottom: 12 }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                  <strong>{b.name}</strong>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => handleEdit(b)} style={btnSmall}>Edit</button>
                    <button onClick={() => handleDelete(b.id)} style={{ ...btnSmall, background: "#fee2e2" }}>Delete</button>
                  </div>
                </div>
                <div style={{ fontSize: 12, color: "#555" }}>
                  <span>Role: <b>{b.role_type}</b></span> ·{" "}
                  <span style={{ color: b.active ? "#16a34a" : "#dc2626" }}>{b.active ? "Active" : "Inactive"}</span>
                </div>
                {b.groups_json.length > 0 && (
                  <div style={{ marginTop: 6, fontSize: 12 }}>
                    <b>Groups:</b> {b.groups_json.join(", ")}
                  </div>
                )}
                {b.classroom_courses_json.length > 0 && (
                  <div style={{ marginTop: 4, fontSize: 12 }}>
                    <b>Courses:</b> {b.classroom_courses_json.join(", ")}
                  </div>
                )}
              </div>
            ))
          )}
        </div>

        <div style={{ flex: "0 0 340px", border: "1px solid #d1d5db", borderRadius: 8, padding: 20, height: "fit-content" }}>
          <h3 style={{ marginTop: 0 }}>{editingId ? "Edit Bundle" : "New Bundle"}</h3>
          <form onSubmit={handleSubmit}>
            <label style={lbl}>Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} required style={inp} />

            <label style={lbl}>Default Role</label>
            <select value={form.role_type} onChange={(e) => setForm({ ...form, role_type: e.target.value })} style={inp}>
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
              <option value="member">Member</option>
            </select>

            <label style={lbl}>Group Emails (comma-separated)</label>
            <textarea value={form.groups_json} onChange={(e) => setForm({ ...form, groups_json: e.target.value })} style={{ ...inp, height: 60, resize: "vertical" }} placeholder="group1@domain.edu, group2@domain.edu" />

            <label style={lbl}>Course IDs (comma-separated)</label>
            <textarea value={form.classroom_courses_json} onChange={(e) => setForm({ ...form, classroom_courses_json: e.target.value })} style={{ ...inp, height: 60, resize: "vertical" }} placeholder="123456789, 987654321" />

            <label style={lbl}>Description</label>
            <input value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} style={inp} />

            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginTop: 10 }}>
              <input type="checkbox" checked={form.active} onChange={(e) => setForm({ ...form, active: e.target.checked })} />
              Active
            </label>

            <div style={{ display: "flex", gap: 8, marginTop: 14 }}>
              <button type="submit" disabled={saving} style={{ flex: 1, padding: "8px 0", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}>
                {saving ? "Saving…" : editingId ? "Update" : "Create"}
              </button>
              {editingId && (
                <button type="button" onClick={() => { setEditingId(null); setForm(emptyForm); }} style={{ padding: "8px 14px", background: "#f3f4f6", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer" }}>
                  Cancel
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}

const lbl: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 3, marginTop: 10 };
const inp: React.CSSProperties = { width: "100%", padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 5, fontSize: 13, boxSizing: "border-box" };
const btnSmall: React.CSSProperties = { fontSize: 12, padding: "3px 10px", background: "#e0e7ff", border: "none", borderRadius: 4, cursor: "pointer" };
