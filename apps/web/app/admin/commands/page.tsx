"use client";

import { useState } from "react";
import GoogleScopePrompt from "../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../lib/api";

type CommandType =
  | "ADD_USER_TO_GROUP"
  | "REMOVE_USER_FROM_GROUP"
  | "ADD_STUDENT_TO_COURSE"
  | "ADD_TEACHER_TO_COURSE"
  | "REMOVE_STUDENT_FROM_COURSE"
  | "REMOVE_TEACHER_FROM_COURSE"
  | "LIST_COURSE_ROSTER"
  | "ENROLL_GROUP_TO_COURSE"
  | "APPLY_ONBOARDING_BUNDLE"
  | "CSV_IMPORT";

export default function CommandsPage() {
  const [commandType, setCommandType] = useState<CommandType>("ADD_USER_TO_GROUP");
  const [params, setParams] = useState<Record<string, string>>({});
  const [dryRun, setDryRun] = useState(false);
  const [preview, setPreview] = useState<Record<string, unknown> | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const [scopeError, setScopeError] = useState<ApiError | null>(null);

  // CSV state
  const [csvText, setCsvText] = useState("");
  const [csvPreview, setCsvPreview] = useState<Record<string, unknown> | null>(null);

  const p = (key: string) => params[key] || "";
  const sp = (key: string) => (v: string) => setParams({ ...params, [key]: v });

  const handlePreview = async () => {
    if (commandType === "LIST_COURSE_ROSTER" && !p("course_id").trim()) {
      setMsg("Course ID is required.");
      return;
    }
    setLoading(true);
    setPreview(null);
    setMsg("");
    setScopeError(null);
    try {
      const res = commandType === "LIST_COURSE_ROSTER"
        ? await api.classroomRoster(p("course_id"))
        : await api.commandPreview(commandType, buildParams());
      setPreview(res);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
        setMsg("Additional Google permission is required for this preview action.");
        return;
      }
      setMsg("Preview failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  const handleRun = async () => {
    if (commandType === "LIST_COURSE_ROSTER" && !p("course_id").trim()) {
      setMsg("Course ID is required.");
      return;
    }
    setLoading(true);
    setResult(null);
    setMsg("");
    setScopeError(null);
    try {
      const res = commandType === "LIST_COURSE_ROSTER"
        ? await api.classroomRoster(p("course_id"))
        : await api.commandRun(commandType, buildParams(), dryRun);
      setResult(res);
      if (commandType === "LIST_COURSE_ROSTER") {
        setMsg("Course roster loaded.");
      } else {
        setMsg(dryRun ? "Dry run job created." : "Job queued successfully.");
      }
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
        setMsg("Additional Google permission is required for this command.");
        return;
      }
      setMsg("Run failed: " + (e instanceof Error ? e.message : String(e)));
    } finally {
      setLoading(false);
    }
  };

  const handleCsvPreview = async () => {
    setLoading(true);
    setCsvPreview(null);
    setMsg("");
    setScopeError(null);
    try {
      const res = await api.csvPreview(csvText);
      setCsvPreview(res);
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
        setMsg("Additional Google permission is required for CSV preview.");
        return;
      }
      setMsg("CSV preview failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleCsvRun = async () => {
    setLoading(true);
    setMsg("");
    setScopeError(null);
    try {
      const res = await api.csvRun(csvText, undefined, dryRun);
      setResult(res);
      setMsg("CSV job queued.");
    } catch (e: unknown) {
      if (isGoogleScopeMissingError(e)) {
        setScopeError(e);
        setMsg("Additional Google permission is required for CSV run.");
        return;
      }
      setMsg("CSV run failed.");
    } finally {
      setLoading(false);
    }
  };

  const buildParams = (): Record<string, unknown> => params;

  const COMMANDS: CommandType[] = [
    "ADD_USER_TO_GROUP",
    "REMOVE_USER_FROM_GROUP",
    "ADD_STUDENT_TO_COURSE",
    "ADD_TEACHER_TO_COURSE",
    "REMOVE_STUDENT_FROM_COURSE",
    "REMOVE_TEACHER_FROM_COURSE",
    "LIST_COURSE_ROSTER",
    "ENROLL_GROUP_TO_COURSE",
    "APPLY_ONBOARDING_BUNDLE",
    "CSV_IMPORT",
  ];

  return (
    <div>
      <h1>Command Runner</h1>
      {msg && (
        <div style={{ marginBottom: 12, padding: "8px 12px", background: "#f0f9ff", borderRadius: 6, fontSize: 13 }}>{msg}</div>
      )}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 20 }}>
        {COMMANDS.map((c) => (
          <button
            key={c}
            onClick={() => { setCommandType(c); setParams({}); setPreview(null); setResult(null); }}
            style={{
              padding: "7px 14px",
              background: commandType === c ? "#2563eb" : "#f3f4f6",
              color: commandType === c ? "#fff" : "#374151",
              border: "1px solid #d1d5db",
              borderRadius: 6,
              cursor: "pointer",
              fontSize: 13,
              fontWeight: commandType === c ? 700 : 400,
            }}
          >
            {c.replace(/_/g, " ")}
          </button>
        ))}
      </div>

      {commandType === "CSV_IMPORT" ? (
        <CsvPanel
          csvText={csvText}
          onCsvChange={setCsvText}
          dryRun={dryRun}
          onDryRunChange={setDryRun}
          onPreview={handleCsvPreview}
          onRun={handleCsvRun}
          csvPreview={csvPreview}
          result={result}
          loading={loading}
        />
      ) : (
        <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
          <div style={{ flex: "0 0 360px", border: "1px solid #d1d5db", borderRadius: 8, padding: 20 }}>
            <h3 style={{ marginTop: 0, fontSize: 15 }}>{commandType.replace(/_/g, " ")}</h3>
            <ParamFields commandType={commandType} p={p} sp={sp} />
            <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginTop: 12 }}>
              <input type="checkbox" checked={dryRun} onChange={(e) => setDryRun(e.target.checked)} />
              Dry Run (no changes)
            </label>
            <div style={{ display: "flex", gap: 8, marginTop: 16 }}>
              <button onClick={handlePreview} disabled={loading} style={btnOutline}>
                Preview
              </button>
              <button onClick={handleRun} disabled={loading} style={btnPrimary}>
                {loading ? "Running…" : "Run"}
              </button>
            </div>
          </div>

          {preview && (
            <div style={{ flex: 1, border: "1px solid #d1d5db", borderRadius: 8, padding: 20 }}>
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Preview</h3>
              <pre style={{ fontSize: 12, background: "#f9fafb", padding: 12, borderRadius: 6, overflow: "auto" }}>
                {JSON.stringify(preview, null, 2)}
              </pre>
            </div>
          )}

          {result && (
            <div style={{ flex: 1, border: "1px solid #d1d5db", borderRadius: 8, padding: 20 }}>
              <h3 style={{ marginTop: 0, fontSize: 14 }}>Job Created</h3>
              <pre style={{ fontSize: 12, background: "#f0fdf4", padding: 12, borderRadius: 6, overflow: "auto" }}>
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ParamFields({
  commandType,
  p,
  sp,
}: {
  commandType: CommandType;
  p: (k: string) => string;
  sp: (k: string) => (v: string) => void;
}) {
  const F = ({ label, k, placeholder, type = "text" }: { label: string; k: string; placeholder?: string; type?: string }) => (
    <div>
      <label style={lbl}>{label}</label>
      <input type={type} value={p(k)} onChange={(e) => sp(k)(e.target.value)} placeholder={placeholder} style={inp} />
    </div>
  );

  if (commandType === "ADD_USER_TO_GROUP" || commandType === "REMOVE_USER_FROM_GROUP") {
    return (
      <>
        <F label="Group Email" k="group_email" placeholder="group@domain.edu" type="email" />
        <F label="User Email" k="user_email" placeholder="user@domain.edu" type="email" />
      </>
    );
  }
  if (commandType === "ADD_STUDENT_TO_COURSE") {
    return (
      <>
        <F label="Course ID" k="course_id" placeholder="123456789" />
        <F label="Student Email" k="student_email" placeholder="student@domain.edu" type="email" />
      </>
    );
  }
  if (commandType === "REMOVE_STUDENT_FROM_COURSE") {
    return (
      <>
        <F label="Course ID" k="course_id" placeholder="123456789" />
        <F label="Student Email" k="student_email" placeholder="student@domain.edu" type="email" />
      </>
    );
  }
  if (commandType === "ADD_TEACHER_TO_COURSE") {
    return (
      <>
        <F label="Course ID" k="course_id" placeholder="123456789" />
        <F label="Teacher Email" k="teacher_email" placeholder="teacher@domain.edu" type="email" />
      </>
    );
  }
  if (commandType === "REMOVE_TEACHER_FROM_COURSE") {
    return (
      <>
        <F label="Course ID" k="course_id" placeholder="123456789" />
        <F label="Teacher Email" k="teacher_email" placeholder="teacher@domain.edu" type="email" />
      </>
    );
  }
  if (commandType === "LIST_COURSE_ROSTER") {
    return (
      <>
        <F label="Course ID" k="course_id" placeholder="123456789" />
      </>
    );
  }
  if (commandType === "ENROLL_GROUP_TO_COURSE") {
    return (
      <>
        <F label="Group Email" k="group_email" placeholder="group@domain.edu" type="email" />
        <F label="Course ID" k="course_id" placeholder="123456789" />
        <div>
          <label style={lbl}>Role</label>
          <select
            value={p("role") || "student"}
            onChange={(e) => sp("role")(e.target.value)}
            style={inp}
          >
            <option value="student">Student</option>
            <option value="teacher">Teacher</option>
          </select>
        </div>
      </>
    );
  }
  if (commandType === "APPLY_ONBOARDING_BUNDLE") {
    return (
      <>
        <F label="User Email" k="user_email" placeholder="user@domain.edu" type="email" />
        <F label="Bundle ID" k="bundle_id" placeholder="1" />
      </>
    );
  }
  return null;
}

function CsvPanel({
  csvText, onCsvChange, dryRun, onDryRunChange, onPreview, onRun, csvPreview, result, loading,
}: {
  csvText: string;
  onCsvChange: (v: string) => void;
  dryRun: boolean;
  onDryRunChange: (v: boolean) => void;
  onPreview: () => void;
  onRun: () => void;
  csvPreview: Record<string, unknown> | null;
  result: Record<string, unknown> | null;
  loading: boolean;
}) {
  return (
    <div>
      <p style={{ fontSize: 13, color: "#555", marginTop: 0 }}>
        Paste CSV with headers: <code>email, name, role, bundle, extra_groups, extra_courses</code>
      </p>
      <textarea
        value={csvText}
        onChange={(e) => onCsvChange(e.target.value)}
        rows={10}
        style={{ width: "100%", fontFamily: "monospace", fontSize: 12, padding: 10, border: "1px solid #d1d5db", borderRadius: 6, boxSizing: "border-box" }}
        placeholder={"email,name,role,bundle\nstudent1@school.edu,Alice,student,1\n"}
      />
      <label style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 13, marginTop: 8 }}>
        <input type="checkbox" checked={dryRun} onChange={(e) => onDryRunChange(e.target.checked)} />
        Dry Run
      </label>
      <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
        <button onClick={onPreview} disabled={loading || !csvText.trim()} style={btnOutline}>Preview CSV</button>
        <button onClick={onRun} disabled={loading || !csvText.trim()} style={btnPrimary}>Run Import</button>
      </div>
      {csvPreview && (
        <div style={{ marginTop: 20, border: "1px solid #d1d5db", borderRadius: 8, padding: 16 }}>
          <h4 style={{ margin: "0 0 8px" }}>Preview: {String(csvPreview.valid_rows)} valid rows, {String(csvPreview.error_rows)} errors</h4>
          <pre style={{ fontSize: 11, background: "#f9fafb", padding: 12, borderRadius: 6, overflow: "auto", maxHeight: 300 }}>
            {JSON.stringify(csvPreview, null, 2)}
          </pre>
        </div>
      )}
      {result && (
        <div style={{ marginTop: 20, border: "1px solid #d1d5db", borderRadius: 8, padding: 16 }}>
          <h4 style={{ margin: "0 0 8px" }}>Job Created</h4>
          <pre style={{ fontSize: 11, background: "#f0fdf4", padding: 12, borderRadius: 6, overflow: "auto", maxHeight: 300 }}>
            {JSON.stringify(result, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

const lbl: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 3, marginTop: 10 };
const inp: React.CSSProperties = { width: "100%", padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 5, fontSize: 13, boxSizing: "border-box" };
const btnPrimary: React.CSSProperties = { flex: 1, padding: "8px 0", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontSize: 13 };
const btnOutline: React.CSSProperties = { flex: 1, padding: "8px 0", background: "#fff", color: "#374151", border: "1px solid #d1d5db", borderRadius: 6, cursor: "pointer", fontSize: 13 };
