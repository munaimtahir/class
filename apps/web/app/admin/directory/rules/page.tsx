"use client";

import { useEffect, useState } from "react";
import { api } from "../../../../lib/api";

type OuTemplate = {
  id: number;
  name: string;
  user_category: string;
  department: string;
  program: string;
  batch: string;
  year: string;
  target_org_unit_path: string;
  priority: number;
  is_active: boolean;
};

type EmailRule = {
  id: number;
  name: string;
  user_category: string;
  department: string;
  program: string;
  batch: string;
  year: string;
  email_pattern: string;
  domain: string;
  collision_strategy: string;
  priority: number;
  is_active: boolean;
};

const defaultOu = {
  name: "",
  user_category: "student",
  department: "",
  program: "",
  batch: "",
  year: "",
  target_org_unit_path: "",
  priority: 100,
  is_active: true,
};

const defaultEmail = {
  name: "",
  user_category: "student",
  department: "",
  program: "",
  batch: "",
  year: "",
  email_pattern: "{given_name}.{family_name}",
  domain: "",
  collision_strategy: "append_numeric",
  priority: 100,
  is_active: true,
};

export default function DirectoryRulesPage() {
  const [ouTemplates, setOuTemplates] = useState<OuTemplate[]>([]);
  const [emailRules, setEmailRules] = useState<EmailRule[]>([]);
  const [ouForm, setOuForm] = useState(defaultOu);
  const [emailForm, setEmailForm] = useState(defaultEmail);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const [ou, er] = await Promise.all([api.listOuTemplates(), api.listEmailTemplates()]);
      setOuTemplates(ou || []);
      setEmailRules(er || []);
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to load rule pages.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveOu = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    try {
      await api.createOuTemplate(ouForm);
      setOuForm(defaultOu);
      await load();
      setMsg("OU template saved.");
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to save OU template.");
    }
  };

  const saveEmail = async (e: React.FormEvent) => {
    e.preventDefault();
    setMsg("");
    try {
      await api.createEmailTemplate(emailForm);
      setEmailForm(defaultEmail);
      await load();
      setMsg("Email template rule saved.");
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to save email template rule.");
    }
  };

  const quickToggleOu = async (row: OuTemplate) => {
    try {
      await api.updateOuTemplate(row.id, { is_active: !row.is_active });
      await load();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to update OU template.");
    }
  };

  const quickToggleEmail = async (row: EmailRule) => {
    try {
      await api.updateEmailTemplate(row.id, { is_active: !row.is_active });
      await load();
    } catch (e: unknown) {
      setMsg(e instanceof Error ? e.message : "Failed to update email rule.");
    }
  };

  return (
    <div>
      <h1 style={{ marginBottom: 8 }}>OU Templates & Email Rules</h1>
      <p style={{ color: "#4b5563", marginTop: 0 }}>
        Rule-driven target OU and generated email format controls. Changes are admin-restricted by API.
      </p>
      {msg && <div style={notice}>{msg}</div>}

      {loading ? (
        <p>Loading…</p>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(420px, 1fr))", gap: 18 }}>
          <section style={card}>
            <h3 style={{ marginTop: 0 }}>OU Templates</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginBottom: 10 }}>
              <thead>
                <tr style={{ background: "#f3f4f6" }}>
                  <th style={th}>Name</th>
                  <th style={th}>Category</th>
                  <th style={th}>Target OU</th>
                  <th style={th}>Priority</th>
                  <th style={th}>Active</th>
                </tr>
              </thead>
              <tbody>
                {ouTemplates.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={td}>{r.name}</td>
                    <td style={td}>{r.user_category}</td>
                    <td style={td}>{r.target_org_unit_path}</td>
                    <td style={td}>{r.priority}</td>
                    <td style={td}>
                      <button onClick={() => quickToggleOu(r)} style={miniBtn}>
                        {r.is_active ? "Disable" : "Enable"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <form onSubmit={saveOu}>
              <RuleFields values={ouForm} setValues={setOuForm} includeOu />
              <button type="submit" style={btnPrimary}>Create OU Template</button>
            </form>
          </section>

          <section style={card}>
            <h3 style={{ marginTop: 0 }}>Email Template Rules</h3>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12, marginBottom: 10 }}>
              <thead>
                <tr style={{ background: "#f3f4f6" }}>
                  <th style={th}>Name</th>
                  <th style={th}>Category</th>
                  <th style={th}>Pattern</th>
                  <th style={th}>Domain</th>
                  <th style={th}>Active</th>
                </tr>
              </thead>
              <tbody>
                {emailRules.map((r) => (
                  <tr key={r.id} style={{ borderBottom: "1px solid #e5e7eb" }}>
                    <td style={td}>{r.name}</td>
                    <td style={td}>{r.user_category}</td>
                    <td style={td}>{r.email_pattern}</td>
                    <td style={td}>{r.domain}</td>
                    <td style={td}>
                      <button onClick={() => quickToggleEmail(r)} style={miniBtn}>
                        {r.is_active ? "Disable" : "Enable"}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <form onSubmit={saveEmail}>
              <RuleFields values={emailForm} setValues={setEmailForm} includeOu={false} />
              <label style={lbl}>Email pattern</label>
              <input
                value={emailForm.email_pattern}
                onChange={(e) => setEmailForm({ ...emailForm, email_pattern: e.target.value })}
                style={input}
              />
              <label style={lbl}>Domain</label>
              <input
                value={emailForm.domain}
                onChange={(e) => setEmailForm({ ...emailForm, domain: e.target.value })}
                style={input}
                required
              />
              <label style={lbl}>Collision strategy</label>
              <select
                value={emailForm.collision_strategy}
                onChange={(e) => setEmailForm({ ...emailForm, collision_strategy: e.target.value })}
                style={input}
              >
                <option value="append_numeric">append_numeric</option>
                <option value="fail">fail</option>
              </select>
              <button type="submit" style={btnPrimary}>Create Email Rule</button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}

function RuleFields({
  values,
  setValues,
  includeOu,
}: {
  values: any;
  setValues: (next: any) => void;
  includeOu: boolean;
}) {
  return (
    <>
      <label style={lbl}>Name</label>
      <input value={values.name} onChange={(e) => setValues({ ...values, name: e.target.value })} style={input} required />
      <label style={lbl}>User category</label>
      <select value={values.user_category} onChange={(e) => setValues({ ...values, user_category: e.target.value })} style={input}>
        <option value="student">student</option>
        <option value="faculty">faculty</option>
        <option value="staff">staff</option>
        <option value="other">other</option>
      </select>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
        <div>
          <label style={lbl}>Department</label>
          <input value={values.department} onChange={(e) => setValues({ ...values, department: e.target.value })} style={input} />
        </div>
        <div>
          <label style={lbl}>Program</label>
          <input value={values.program} onChange={(e) => setValues({ ...values, program: e.target.value })} style={input} />
        </div>
        <div>
          <label style={lbl}>Batch</label>
          <input value={values.batch} onChange={(e) => setValues({ ...values, batch: e.target.value })} style={input} />
        </div>
        <div>
          <label style={lbl}>Year</label>
          <input value={values.year} onChange={(e) => setValues({ ...values, year: e.target.value })} style={input} />
        </div>
      </div>
      {includeOu && (
        <>
          <label style={lbl}>Target OU path</label>
          <input value={values.target_org_unit_path} onChange={(e) => setValues({ ...values, target_org_unit_path: e.target.value })} style={input} required />
        </>
      )}
      <label style={lbl}>Priority</label>
      <input
        type="number"
        value={values.priority}
        onChange={(e) => setValues({ ...values, priority: Number(e.target.value) || 100 })}
        style={input}
      />
      <label style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, fontSize: 13 }}>
        <input
          type="checkbox"
          checked={values.is_active}
          onChange={(e) => setValues({ ...values, is_active: e.target.checked })}
        />
        Active
      </label>
    </>
  );
}

const card: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 10, padding: 14, background: "#fff" };
const th: React.CSSProperties = { textAlign: "left", padding: "6px 8px" };
const td: React.CSSProperties = { padding: "6px 8px" };
const lbl: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginTop: 8, marginBottom: 3 };
const input: React.CSSProperties = { width: "100%", padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 6, fontSize: 13, boxSizing: "border-box" };
const miniBtn: React.CSSProperties = { fontSize: 11, padding: "3px 8px", borderRadius: 4, border: "1px solid #d1d5db", background: "#fff", cursor: "pointer" };
const btnPrimary: React.CSSProperties = { marginTop: 12, padding: "8px 12px", background: "#1d4ed8", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" };
const notice: React.CSSProperties = { marginBottom: 10, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 };
