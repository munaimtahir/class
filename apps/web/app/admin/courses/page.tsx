"use client";

import { useEffect, useState, useCallback } from "react";
import GoogleScopePrompt from "../../_components/GoogleScopePrompt";
import { api, ApiError, isGoogleScopeMissingError } from "../../../lib/api";
import { phase2bApi } from "../../../lib/api";
import ConfirmModal from "./_components/ConfirmModal";

type Course = {
  id: string;
  name: string;
  section?: string;
  courseState: string;
  ownerId?: string;
};

type CourseRoster = {
  course_id: string;
  students: string[];
  teachers: string[];
  student_count: number;
  teacher_count: number;
  total_count: number;
};

type Confirm = {
  title: string;
  message: string;
  confirmLabel: string;
  danger?: boolean;
  action: () => Promise<void>;
} | null;

function stateBadge(state: string) {
  const color =
    state === "ACTIVE" ? "#16a34a" :
    state === "ARCHIVED" ? "#b45309" :
    state === "DELETED" ? "#dc2626" : "#6b7280";
  return (
    <span style={{ fontSize: 11, fontWeight: 700, color, background: color + "18", padding: "2px 7px", borderRadius: 12 }}>
      {state}
    </span>
  );
}

export default function CoursesAdminPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<{ text: string; ok: boolean } | null>(null);
  const [scopeError, setScopeError] = useState<ApiError | null>(null);
  const [selectedId, setSelectedId] = useState("");
  const [confirm, setConfirm] = useState<Confirm>(null);
  const [busy, setBusy] = useState(false);
  const [roster, setRoster] = useState<CourseRoster | null>(null);
  const [rosterLoading, setRosterLoading] = useState(false);

  // Quick enroll / remove forms
  const [enrollEmail, setEnrollEmail] = useState("");
  const [enrollRole, setEnrollRole] = useState<"student" | "teacher">("student");

  // Create course form
  const [showCreate, setShowCreate] = useState(false);
  const [createName, setCreateName] = useState("");
  const [createSection, setCreateSection] = useState("");
  const [createRoom, setCreateRoom] = useState("");
  const [createDesc, setCreateDesc] = useState("");
  const [creating, setCreating] = useState(false);

  // Remove member form
  const [removeEmail, setRemoveEmail] = useState("");
  const [removeRole, setRemoveRole] = useState<"student" | "teacher">("student");

  const flash = (text: string, ok = true) => setMsg({ text, ok });

  const loadRoster = useCallback(async (courseId: string) => {
    if (!courseId) {
      setRoster(null);
      return;
    }
    setRosterLoading(true);
    try {
      setScopeError(null);
      const data = await api.classroomRoster(courseId);
      setRoster(data);
    } catch (err: unknown) {
      if (isGoogleScopeMissingError(err)) {
        setScopeError(err);
        setMsg({ text: err.message, ok: false });
        setRoster(null);
        return;
      }
      const errMsg = err instanceof Error ? err.message : "Failed to load roster.";
      setMsg({ text: errMsg, ok: false });
      setRoster(null);
    } finally {
      setRosterLoading(false);
    }
  }, []);

  const loadCourses = useCallback(() => {
    setLoading(true);
    setScopeError(null);
    api.adminCourses()
      .then((d) => setCourses(d.courses || []))
      .catch((err: unknown) => {
        if (isGoogleScopeMissingError(err)) {
          setScopeError(err);
          flash("Additional Google permission is required to list Classroom courses.", false);
          return;
        }
        flash("Failed to load courses.", false);
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadCourses(); }, [loadCourses]);
  useEffect(() => {
    if (!selectedId) {
      setRoster(null);
      return;
    }
    loadRoster(selectedId);
  }, [selectedId, loadRoster]);

  const runWithConfirm = (opts: Exclude<Confirm, null>) => {
    if (!opts) return;
    setConfirm(opts as Confirm);
  };

  const execConfirmed = async () => {
    if (!confirm) return;
    setBusy(true);
    setConfirm(null);
    try {
      await confirm.action();
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Operation failed.";
      flash(errMsg, false);
    } finally {
      setBusy(false);
    }
  };

  const handleEnroll = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !enrollEmail) return;
    setBusy(true);
    setMsg(null);
    try {
      setScopeError(null);
      if (enrollRole === "student") {
        await api.addStudent(selectedId, enrollEmail);
      } else {
        await api.addTeacher(selectedId, enrollEmail);
      }
      flash(`✅ ${enrollEmail} added as ${enrollRole} in course ${selectedId}`);
      await loadRoster(selectedId);
    } catch (err: unknown) {
      if (isGoogleScopeMissingError(err)) {
        setScopeError(err);
        flash("Additional Google permission is required to manage Classroom roster access.", false);
      } else {
        flash("❌ Enrollment failed. Check email and try again.", false);
      }
    } finally {
      setBusy(false);
    }
  };

  const handleCreateCourse = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createName.trim()) return;
    setCreating(true);
    setMsg(null);
    try {
      setScopeError(null);
      await phase2bApi.createCourse({
        name: createName.trim(),
        section: createSection.trim(),
        room: createRoom.trim(),
        description: createDesc.trim(),
      });
      flash(`✅ Course "${createName}" created successfully.`);
      setCreateName(""); setCreateSection(""); setCreateRoom(""); setCreateDesc("");
      setShowCreate(false);
      loadCourses();
    } catch (err: unknown) {
      if (isGoogleScopeMissingError(err)) {
        setScopeError(err);
        flash("Additional Google permission is required to create Classroom courses.", false);
      } else {
        flash("❌ Failed to create course.", false);
      }
    } finally {
      setCreating(false);
    }
  };

  const handleArchive = (course: Course) => {
    if (course.courseState === "ARCHIVED") {
      flash("Course is already archived.", false);
      return;
    }
    runWithConfirm({
      title: "Archive Course",
      message: `Archive "${course.name}"? Students and teachers will lose access. This can be undone by Google Workspace admins.`,
      confirmLabel: "Archive Course",
      danger: true,
      action: async () => {
        await phase2bApi.archiveCourse(course.id);
        flash(`✅ Course "${course.name}" archived.`);
        loadCourses();
      },
    });
  };

  const handleDelete = (course: Course) => {
    if (course.courseState !== "ARCHIVED") {
      flash("Only ARCHIVED courses can be deleted. Archive it first.", false);
      return;
    }
    runWithConfirm({
      title: "⚠️ Permanently Delete Course",
      message: `DELETE "${course.name}" permanently? This cannot be undone. The course must already be archived.`,
      confirmLabel: "Permanently Delete",
      danger: true,
      action: async () => {
        await phase2bApi.deleteCourse(course.id);
        flash(`✅ Course "${course.name}" deleted.`);
        setSelectedId("");
        loadCourses();
      },
    });
  };

  const handleRemoveMember = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedId || !removeEmail) return;
    const label = removeRole === "student" ? "student" : "teacher";
    runWithConfirm({
      title: `Remove ${label.charAt(0).toUpperCase() + label.slice(1)} — Direct Admin Action`,
      message: `Remove "${removeEmail}" as a ${label} from course ${selectedId}? This is a direct admin operation.`,
      confirmLabel: `Remove ${label}`,
      danger: true,
      action: async () => {
        if (removeRole === "student") {
          await phase2bApi.removeStudent(selectedId, removeEmail);
        } else {
          await phase2bApi.removeTeacher(selectedId, removeEmail);
        }
        flash(`✅ ${removeEmail} removed as ${label} from course ${selectedId}`);
        setRemoveEmail("");
        await loadRoster(selectedId);
      },
    });
  };

  const selected = courses.find((c) => c.id === selectedId);

  return (
    <div>
      <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Classroom Admin — Courses</h1>
        <button
          onClick={() => setShowCreate((v) => !v)}
          style={{ padding: "8px 16px", background: "#16a34a", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}
        >
          {showCreate ? "Cancel" : "+ New Course"}
        </button>
        <button
          onClick={loadCourses}
          style={{ padding: "8px 14px", border: "1px solid #d1d5db", background: "#fff", borderRadius: 6, cursor: "pointer" }}
        >
          ↻ Refresh
        </button>
        {busy && <span style={{ fontSize: 13, color: "#6b7280" }}>Working…</span>}
      </div>

      {msg && (
        <div style={{ marginBottom: 14, padding: "9px 14px", background: msg.ok ? "#f0fdf4" : "#fef2f2", border: `1px solid ${msg.ok ? "#bbf7d0" : "#fecaca"}`, borderRadius: 6, fontSize: 13, color: msg.ok ? "#15803d" : "#b91c1c" }}>
          {msg.text}
        </div>
      )}
      {scopeError && <GoogleScopePrompt error={scopeError} />}

      {/* Create course form */}
      {showCreate && (
        <div style={{ border: "1px solid #a7f3d0", borderRadius: 8, padding: 20, marginBottom: 20, background: "#f0fdf4", maxWidth: 560 }}>
          <h3 style={{ margin: "0 0 14px" }}>Create New Classroom Course</h3>
          <form onSubmit={handleCreateCourse}>
            <label style={labelStyle}>Course Name <span style={{ color: "#dc2626" }}>*</span></label>
            <input value={createName} onChange={(e) => setCreateName(e.target.value)} placeholder="e.g. Biology 101" required style={inputStyle} />
            <label style={labelStyle}>Section</label>
            <input value={createSection} onChange={(e) => setCreateSection(e.target.value)} placeholder="e.g. Period 3" style={inputStyle} />
            <label style={labelStyle}>Room</label>
            <input value={createRoom} onChange={(e) => setCreateRoom(e.target.value)} placeholder="e.g. Room 204" style={inputStyle} />
            <label style={labelStyle}>Description</label>
            <input value={createDesc} onChange={(e) => setCreateDesc(e.target.value)} placeholder="Optional description" style={inputStyle} />
            <button
              type="submit"
              disabled={creating || !createName.trim()}
              style={{ marginTop: 14, padding: "9px 22px", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer", fontWeight: 600 }}
            >
              {creating ? "Creating…" : "Create Course"}
            </button>
          </form>
        </div>
      )}

      <div style={{ display: "flex", gap: 24, flexWrap: "wrap" }}>
        {/* Course list */}
        <div style={{ flex: "1 1 520px" }}>
          {loading ? (
            <p>Loading…</p>
          ) : courses.length === 0 ? (
            <p style={{ color: "#666" }}>No courses found.</p>
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead>
                <tr style={{ background: "#f3f4f6" }}>
                  <th style={th}>Name</th>
                  <th style={th}>Section</th>
                  <th style={th}>State</th>
                  <th style={th}>ID</th>
                  <th style={th}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {courses.map((c) => (
                  <tr
                    key={c.id}
                    onClick={() => setSelectedId(c.id)}
                    style={{ borderBottom: "1px solid #e5e7eb", cursor: "pointer", background: selectedId === c.id ? "#eff6ff" : undefined }}
                  >
                    <td style={td}>{c.name}</td>
                    <td style={td}>{c.section || "—"}</td>
                    <td style={td}>{stateBadge(c.courseState)}</td>
                    <td style={td}><code style={{ fontSize: 11 }}>{c.id}</code></td>
                    <td style={td}>
                      <div style={{ display: "flex", gap: 6 }}>
                        {c.courseState !== "ARCHIVED" && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleArchive(c); }}
                            style={{ ...actionBtn, color: "#92400e", background: "#fef3c7", border: "1px solid #fde68a" }}
                          >
                            Archive
                          </button>
                        )}
                        {c.courseState === "ARCHIVED" && (
                          <button
                            onClick={(e) => { e.stopPropagation(); handleDelete(c); }}
                            style={{ ...actionBtn, color: "#dc2626", background: "#fef2f2", border: "1px solid #fecaca" }}
                          >
                            Delete
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

        {/* Side panels */}
        <div style={{ flex: "0 0 310px", display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Enroll panel */}
          <div style={panelStyle}>
            <h3 style={{ marginTop: 0, fontSize: 15 }}>Add to Course</h3>
            <p style={{ margin: "0 0 10px", fontSize: 12, color: "#6b7280" }}>
              Click a course row to select it, then add a student or teacher.
            </p>
            <form onSubmit={handleEnroll}>
              <label style={labelStyle}>Course ID</label>
              <input value={selectedId} onChange={(e) => setSelectedId(e.target.value)} placeholder="Click a course or paste ID" style={inputStyle} />
              <label style={labelStyle}>Email</label>
              <input value={enrollEmail} onChange={(e) => setEnrollEmail(e.target.value)} placeholder="user@domain.edu" type="email" style={inputStyle} />
              <label style={labelStyle}>Role</label>
              <select value={enrollRole} onChange={(e) => setEnrollRole(e.target.value as "student" | "teacher")} style={inputStyle}>
                <option value="student">Student</option>
                <option value="teacher">Teacher</option>
              </select>
              <button
                type="submit"
                disabled={busy || !selectedId || !enrollEmail}
                style={{ width: "100%", marginTop: 10, padding: "9px 0", background: "#2563eb", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
              >
                Add
              </button>
            </form>
          </div>

          {/* Remove panel */}
          <div style={{ ...panelStyle, borderColor: "#fca5a5" }}>
            <h3 style={{ marginTop: 0, fontSize: 15, color: "#b91c1c" }}>⚠ Remove from Course</h3>
            <p style={{ margin: "0 0 10px", fontSize: 12, color: "#6b7280" }}>
              Direct admin removal. Confirmation required.
            </p>
            <form onSubmit={handleRemoveMember}>
              <label style={labelStyle}>Course ID</label>
              <input value={selectedId} onChange={(e) => setSelectedId(e.target.value)} placeholder="Click a course or paste ID" style={inputStyle} />
              <label style={labelStyle}>Email</label>
              <input value={removeEmail} onChange={(e) => setRemoveEmail(e.target.value)} placeholder="user@domain.edu" type="email" style={inputStyle} />
              <label style={labelStyle}>Role</label>
              <select value={removeRole} onChange={(e) => setRemoveRole(e.target.value as "student" | "teacher")} style={inputStyle}>
                <option value="student">Student</option>
                <option value="teacher">Teacher (cannot remove owner)</option>
              </select>
              <button
                type="submit"
                disabled={busy || !selectedId || !removeEmail}
                style={{ width: "100%", marginTop: 10, padding: "9px 0", background: "#dc2626", color: "#fff", border: "none", borderRadius: 6, cursor: "pointer" }}
              >
                Remove
              </button>
            </form>
          </div>

          <div style={{ ...panelStyle, borderColor: "#bfdbfe", background: "#eff6ff" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <h3 style={{ margin: 0, fontSize: 15, color: "#1d4ed8" }}>Enrolled Users</h3>
              <button
                type="button"
                onClick={() => selectedId && loadRoster(selectedId)}
                disabled={!selectedId || rosterLoading}
                style={{ ...actionBtn, border: "1px solid #bfdbfe", background: "#fff", color: "#1e3a8a" }}
              >
                {rosterLoading ? "Loading…" : "Refresh"}
              </button>
            </div>
            {!selectedId ? (
              <p style={{ margin: 0, color: "#6b7280", fontSize: 12 }}>Select a course to list enrolled students and teachers.</p>
            ) : rosterLoading ? (
              <p style={{ margin: 0, color: "#6b7280", fontSize: 12 }}>Loading roster…</p>
            ) : !roster ? (
              <p style={{ margin: 0, color: "#b91c1c", fontSize: 12 }}>Roster unavailable.</p>
            ) : (
              <div style={{ fontSize: 12 }}>
                <div style={{ marginBottom: 8 }}>
                  <b>Total:</b> {roster.total_count} ({roster.student_count} students, {roster.teacher_count} teachers)
                </div>
                <div style={{ marginBottom: 8 }}>
                  <b>Students</b>
                  {roster.students.length === 0 ? (
                    <p style={{ margin: "4px 0 0", color: "#6b7280" }}>No students enrolled.</p>
                  ) : (
                    <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                      {roster.students.map((email) => (
                        <li key={`student-${email}`} style={{ marginBottom: 4 }}>
                          {email}{" "}
                          <button
                            type="button"
                            onClick={() => { setRemoveRole("student"); setRemoveEmail(email); }}
                            style={{ ...actionBtn, marginLeft: 6, border: "1px solid #fecaca", background: "#fff", color: "#b91c1c" }}
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
                <div>
                  <b>Teachers</b>
                  {roster.teachers.length === 0 ? (
                    <p style={{ margin: "4px 0 0", color: "#6b7280" }}>No teachers assigned.</p>
                  ) : (
                    <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
                      {roster.teachers.map((email) => (
                        <li key={`teacher-${email}`} style={{ marginBottom: 4 }}>
                          {email}{" "}
                          <button
                            type="button"
                            onClick={() => { setRemoveRole("teacher"); setRemoveEmail(email); }}
                            style={{ ...actionBtn, marginLeft: 6, border: "1px solid #fecaca", background: "#fff", color: "#b91c1c" }}
                          >
                            Remove
                          </button>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            )}
          </div>

          {selected && (
            <div style={{ ...panelStyle, background: "#f8fafc", borderColor: "#cbd5e1" }}>
              <strong style={{ fontSize: 13 }}>Selected:</strong>
              <p style={{ margin: "4px 0 0", fontSize: 13 }}>{selected.name}</p>
              <p style={{ margin: "2px 0 0", fontSize: 11, color: "#6b7280" }}>{selected.id}</p>
              <p style={{ margin: "2px 0 0" }}>{stateBadge(selected.courseState)}</p>
            </div>
          )}
        </div>
      </div>

      {confirm && (
        <ConfirmModal
          title={confirm.title}
          message={confirm.message}
          confirmLabel={confirm.confirmLabel}
          danger={confirm.danger}
          onConfirm={execConfirmed}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  );
}

const th: React.CSSProperties = { textAlign: "left", padding: "8px 12px", fontWeight: 600, fontSize: 12, color: "#374151" };
const td: React.CSSProperties = { padding: "8px 12px", verticalAlign: "middle" };
const labelStyle: React.CSSProperties = { display: "block", fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 4, marginTop: 10 };
const inputStyle: React.CSSProperties = { width: "100%", padding: "7px 10px", border: "1px solid #d1d5db", borderRadius: 5, fontSize: 13, boxSizing: "border-box" };
const panelStyle: React.CSSProperties = { border: "1px solid #d1d5db", borderRadius: 8, padding: 18 };
const actionBtn: React.CSSProperties = { padding: "3px 10px", fontSize: 12, borderRadius: 5, cursor: "pointer", fontWeight: 600 };
