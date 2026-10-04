"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

// ─── Types ─────────────────────────────────────────────────────────────────

type Course = { id: number; name: string; section: string };

type ParsedSession = {
  course_map_id: number | null;
  date: string | null;
  start_time: string | null;
  end_time: string | null;
  title: string;
  subject: string;
  topic: string;
  subgroup_label: string;
  requires_meet: boolean;
  publish_mode: string;
  scheduled_for: string | null;
  topic_label: string;
};

type PreviewSession = {
  row_index: number;
  parsed: ParsedSession;
  status: "valid" | "invalid" | "duplicate";
  errors: string[];
};

type SheetTab = { title: string; gid: number };

type PreviewResult = {
  preview_token: string;
  spreadsheet_title: string;
  selected_sheet: string;
  available_sheets: SheetTab[];
  target_day: string | null;
  target_date: string | null;
  summary: {
    rows_seen: number;
    filtered_rows: number;
    valid_sessions: number;
    invalid_rows: number;
    duplicates: number;
  };
  sessions: PreviewSession[];
  source_ref: string;
};

type CommitResult = {
  batch_id: number;
  status: string;
  created: number;
  skipped_duplicates: number;
  invalid_rows: number;
  session_draft_ids: number[];
};

type PromoteResult = {
  batch_id: number;
  promoted: number;
  session_ids: number[];
};

// ─── Step indicator ─────────────────────────────────────────────────────────

function Steps({ current }: { current: 1 | 2 | 3 }) {
  const steps = ["Choose Source", "Preview Sessions", "Review & Publish"];
  return (
    <ol className="flex gap-0 mb-6">
      {steps.map((label, i) => {
        const n = i + 1 as 1 | 2 | 3;
        const active = n === current;
        const done = n < current;
        return (
          <li key={n} className="flex items-center">
            <span
              className={`flex items-center justify-center w-7 h-7 rounded-full text-sm font-bold border-2 transition-colors ${
                active
                  ? "bg-teal-600 border-teal-600 text-white"
                  : done
                  ? "bg-teal-100 border-teal-400 text-teal-700"
                  : "bg-white border-slate-300 text-slate-400"
              }`}
            >
              {done ? "✓" : n}
            </span>
            <span
              className={`ml-2 text-sm font-medium ${
                active ? "text-teal-700" : done ? "text-teal-600" : "text-slate-400"
              }`}
            >
              {label}
            </span>
            {n < 3 && <span className="mx-3 text-slate-300 text-lg">›</span>}
          </li>
        );
      })}
    </ol>
  );
}

// ─── Status badge ───────────────────────────────────────────────────────────

function Badge({ status }: { status: PreviewSession["status"] }) {
  const styles: Record<string, string> = {
    valid: "bg-green-100 text-green-800",
    invalid: "bg-red-100 text-red-800",
    duplicate: "bg-amber-100 text-amber-800",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-semibold ${styles[status]}`}>
      {status}
    </span>
  );
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function ImportsPage() {
  const router = useRouter();

  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [importSource, setImportSource] = useState<"google_sheet" | "file">("google_sheet");
  const [courses, setCourses] = useState<Course[]>([]);
  const [loadingCourses, setLoadingCourses] = useState(true);

  // Step 1 form state
  const [sheetUrl, setSheetUrl] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [targetDate, setTargetDate] = useState("");
  const [targetDay, setTargetDay] = useState("");
  const [sheetName, setSheetName] = useState("");
  const [defaultCourseId, setDefaultCourseId] = useState("");
  const [availableTabs, setAvailableTabs] = useState<SheetTab[]>([]);

  // Step 2 preview state
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");
  const [showInvalid, setShowInvalid] = useState(true);
  const [showDuplicates, setShowDuplicates] = useState(false);

  // Step 3 commit state
  const [commitResult, setCommitResult] = useState<CommitResult | null>(null);
  const [promoteResult, setPromoteResult] = useState<PromoteResult | null>(null);
  const [committing, setCommitting] = useState(false);
  const [promoting, setPromoting] = useState(false);
  const [commitError, setCommitError] = useState("");

  useEffect(() => {
    api
      .courses()
      .then((data: Course[]) => setCourses(data))
      .catch(() => {})
      .finally(() => setLoadingCourses(false));
  }, []);

  // ── Step 1 → preview ────────────────────────────────────────────────────

  async function handlePreview(e: React.FormEvent) {
    e.preventDefault();
    if (importSource === "google_sheet" && !sheetUrl.trim()) return;
    if (importSource === "file" && !uploadFile) return;

    setPreviewLoading(true);
    setPreviewError("");
    setPreview(null);

    try {
      let data: PreviewResult;
      if (importSource === "google_sheet") {
        const payload: Record<string, unknown> = { sheet_url: sheetUrl };
        if (targetDate) payload.target_date = targetDate;
        if (targetDay) payload.target_day = targetDay;
        if (sheetName) payload.sheet_name = sheetName;
        if (defaultCourseId) payload.default_course_map_id = Number(defaultCourseId);
        data = await api.previewSheetImport(payload);
      } else {
        const file = uploadFile;
        if (!file) {
          throw new Error("Please choose a CSV or TSV file to preview.");
        }
        const fields: Record<string, string> = {};
        if (targetDate) fields.target_date = targetDate;
        if (targetDay) fields.target_day = targetDay;
        if (defaultCourseId) fields.default_course_map_id = defaultCourseId;
        data = await api.previewFileImport(file, fields);
      }

      setPreview(data);
      if (importSource === "google_sheet" && data.available_sheets.length > 1 && !sheetName) {
        setAvailableTabs(data.available_sheets);
      }
      setStep(2);
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : "Preview failed. Check the URL and try again.";
      setPreviewError(msg);
    } finally {
      setPreviewLoading(false);
    }
  }

  // ── Step 2 → commit ─────────────────────────────────────────────────────

  async function handleCommit() {
    if (!preview) return;
    setCommitting(true);
    setCommitError("");
    try {
      const result: CommitResult = await api.commitSheetImport({
        preview_token: preview.preview_token,
      });
      setCommitResult(result);
      setStep(3);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Import failed. Please try again.";
      setCommitError(msg);
    } finally {
      setCommitting(false);
    }
  }

  // ── Step 3 → promote & go to dashboard ──────────────────────────────────

  async function handlePromote() {
    if (!commitResult) return;
    setPromoting(true);
    try {
      const result: PromoteResult = await api.promoteImportBatch(commitResult.batch_id);
      setPromoteResult(result);
    } catch {
      /* ignore — show fallback below */
    } finally {
      setPromoting(false);
    }
  }

  function goToDashboard() {
    router.push("/classroom/dashboard");
  }

  // ─────────────────────────────────────────────────────────────────────────
  // Render
  // ─────────────────────────────────────────────────────────────────────────

  const validSessions = preview?.sessions.filter((s) => s.status === "valid") ?? [];
  const invalidSessions = preview?.sessions.filter((s) => s.status === "invalid") ?? [];
  const dupeSessions = preview?.sessions.filter((s) => s.status === "duplicate") ?? [];

  const displayRows = preview?.sessions.filter((s) => {
    if (s.status === "valid") return true;
    if (s.status === "invalid" && showInvalid) return true;
    if (s.status === "duplicate" && showDuplicates) return true;
    return false;
  }) ?? [];

  return (
    <main className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-amber-50 p-6">
      <div className="max-w-5xl mx-auto space-y-6">

        {/* Header */}
        <header className="rounded-xl bg-white p-5 shadow border border-slate-200 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Import Timetable</h1>
            <p className="text-sm text-slate-500 mt-1">
              Import an entire day into session drafts from a Google Sheet or uploaded CSV, TSV, XLSX, or XLSM file.
            </p>
          </div>
          <button
            onClick={goToDashboard}
            className="text-sm text-teal-700 hover:underline"
          >
            ← Classroom Dashboard
          </button>
        </header>

        <div className="rounded-xl bg-white p-6 shadow border border-slate-200">
          <Steps current={step} />

          {/* ── STEP 1: Paste link ────────────────────────────────────────── */}
          {step === 1 && (
            <form onSubmit={handlePreview} className="space-y-4 max-w-2xl">
              <div className="rounded-lg border border-teal-200 bg-teal-50 p-4 text-sm text-teal-900">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div>
                    <p className="font-semibold">Import template and expected columns</p>
                    <p className="text-xs text-teal-800 mt-1">
                      Required shape: Day or Date, Time or Start Time plus End Time, and at least one of Title, Subject, or Topic.
                    </p>
                  </div>
                  <a
                    href="/templates/timetable-import-template.csv"
                    download
                    className="rounded-lg bg-white px-3 py-2 text-xs font-semibold text-teal-800 border border-teal-300 hover:bg-teal-100"
                  >
                    Download Template
                  </a>
                </div>
                <div className="mt-3 grid gap-2 text-xs text-teal-900 md:grid-cols-2">
                  <div>
                    <span className="font-semibold">Required columns:</span> Day or Date, Time or Start Time plus End Time, and one of Title, Subject, Topic
                  </div>
                  <div>
                    <span className="font-semibold">Optional columns:</span> Group, Faculty, Room, Notes
                  </div>
                </div>
              </div>

              <div>
                <label className="block text-sm font-medium text-slate-700 mb-2">
                  Import Source
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setImportSource("google_sheet");
                      setUploadFile(null);
                    }}
                    className={`rounded-lg border px-4 py-3 text-left text-sm ${
                      importSource === "google_sheet"
                        ? "border-teal-600 bg-teal-50 text-teal-800"
                        : "border-slate-300 bg-white text-slate-600"
                    }`}
                  >
                    <div className="font-semibold">Google Sheet URL</div>
                    <div className="text-xs mt-1">Use the existing tab-aware import flow.</div>
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      setImportSource("file");
                      setSheetUrl("");
                      setSheetName("");
                      setAvailableTabs([]);
                    }}
                    className={`rounded-lg border px-4 py-3 text-left text-sm ${
                      importSource === "file"
                        ? "border-teal-600 bg-teal-50 text-teal-800"
                        : "border-slate-300 bg-white text-slate-600"
                    }`}
                  >
                    <div className="font-semibold">Upload File</div>
                    <div className="text-xs mt-1">Import a local CSV, TSV, XLSX, or XLSM file with timetable columns.</div>
                  </button>
                </div>
              </div>

              {importSource === "google_sheet" ? (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Google Sheet URL <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="url"
                    required
                    placeholder="https://docs.google.com/spreadsheets/d/..."
                    value={sheetUrl}
                    onChange={(e) => setSheetUrl(e.target.value)}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                  />
                </div>
              ) : (
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Upload File <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="file"
                    accept=".csv,.tsv,.txt,.xlsx,.xlsm,text/csv,text/tab-separated-values,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    required
                    onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                  />
                  <p className="mt-1 text-xs text-slate-500">
                    Supported formats: CSV, TSV, XLSX, and XLSM. For Excel uploads, the first non-empty worksheet is used.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Target Date
                  </label>
                  <input
                    type="date"
                    value={targetDate}
                    onChange={(e) => {
                      setTargetDate(e.target.value);
                      setTargetDay("");
                    }}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Or Weekday
                  </label>
                  <select
                    value={targetDay}
                    onChange={(e) => {
                      setTargetDay(e.target.value);
                      if (e.target.value) setTargetDate("");
                    }}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                  >
                    <option value="">— any day —</option>
                    {["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"].map(
                      (d) => <option key={d} value={d}>{d}</option>
                    )}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    Default Course
                  </label>
                  <select
                    value={defaultCourseId}
                    onChange={(e) => setDefaultCourseId(e.target.value)}
                    className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                  >
                    <option value="">{loadingCourses ? "Loading…" : "— select course —"}</option>
                    {courses.map((c) => (
                      <option key={c.id} value={String(c.id)}>
                        {c.name} {c.section ? `(${c.section})` : ""}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">
                    {importSource === "google_sheet" ? "Sheet Tab (optional)" : "File Format"}
                  </label>
                  {importSource === "google_sheet" ? (
                    availableTabs.length > 0 ? (
                      <select
                        value={sheetName}
                        onChange={(e) => setSheetName(e.target.value)}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                      >
                        <option value="">— first tab —</option>
                        {availableTabs.map((t) => (
                          <option key={t.gid} value={t.title}>{t.title}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="text"
                        placeholder="e.g. Week 3"
                        value={sheetName}
                        onChange={(e) => setSheetName(e.target.value)}
                        className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400"
                      />
                    )
                  ) : (
                    <div className="w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                      Auto-detected from uploaded file
                    </div>
                  )}
                </div>
              </div>

              {previewError && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {previewError}
                </div>
              )}

              <button
                type="submit"
                disabled={previewLoading}
                className="rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 text-sm font-semibold disabled:opacity-60"
              >
                {previewLoading
                  ? importSource === "google_sheet"
                    ? "Fetching sheet…"
                    : "Reading file…"
                  : "Preview Sessions →"}
              </button>
            </form>
          )}

          {/* ── STEP 2: Preview ───────────────────────────────────────────── */}
          {step === 2 && preview && (
            <div className="space-y-4">
              {/* Sheet info */}
              <div className="flex flex-wrap items-center gap-3 text-sm text-slate-600">
                <span className="font-semibold text-slate-800">{preview.spreadsheet_title}</span>
                <span className="rounded bg-slate-100 px-2 py-0.5">{preview.selected_sheet}</span>
                {preview.target_date && (
                  <span className="rounded bg-teal-50 text-teal-800 px-2 py-0.5">
                    {preview.target_date}
                  </span>
                )}
              </div>

              {/* Tab switcher (if multiple) */}
              {importSource === "google_sheet" && preview.available_sheets.length > 1 && (
                <div className="flex flex-wrap gap-2">
                  <span className="text-xs text-slate-500 self-center">Other tabs:</span>
                  {preview.available_sheets.map((t) => (
                    <button
                      key={t.gid}
                      onClick={async () => {
                        setSheetName(t.title);
                        setPreviewLoading(true);
                        setPreviewError("");
                        try {
                          const payload: Record<string, unknown> = {
                            sheet_url: sheetUrl,
                            sheet_name: t.title,
                          };
                          if (targetDate) payload.target_date = targetDate;
                          if (targetDay) payload.target_day = targetDay;
                          if (defaultCourseId) payload.default_course_map_id = Number(defaultCourseId);
                          const data: PreviewResult = await api.previewSheetImport(payload);
                          setPreview(data);
                        } catch (err: unknown) {
                          setPreviewError(err instanceof Error ? err.message : "Preview failed.");
                        } finally {
                          setPreviewLoading(false);
                        }
                      }}
                      className={`text-xs rounded px-2 py-1 border ${
                        t.title === preview.selected_sheet
                          ? "bg-teal-600 text-white border-teal-600"
                          : "bg-white text-slate-600 border-slate-300 hover:border-teal-400"
                      }`}
                    >
                      {t.title}
                    </button>
                  ))}
                </div>
              )}

              {/* Summary cards */}
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                <SummaryCard label="Rows seen" value={preview.summary.rows_seen} />
                <SummaryCard label="Valid" value={preview.summary.valid_sessions} color="green" />
                <SummaryCard label="Invalid" value={preview.summary.invalid_rows} color="red" />
                <SummaryCard label="Duplicates" value={preview.summary.duplicates} color="amber" />
              </div>

              {/* Filter toggles */}
              <div className="flex gap-4 text-sm">
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showInvalid}
                    onChange={(e) => setShowInvalid(e.target.checked)}
                  />
                  Show invalid rows
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showDuplicates}
                    onChange={(e) => setShowDuplicates(e.target.checked)}
                  />
                  Show duplicates
                </label>
              </div>

              {/* Sessions table */}
              <div className="overflow-auto rounded-lg border border-slate-200">
                <table className="min-w-full text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200">
                    <tr>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Row</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Date</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Time</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Title</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Subject</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Topic</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Group</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Meet</th>
                      <th className="px-3 py-2 text-left text-slate-600 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {displayRows.length === 0 && (
                      <tr>
                        <td colSpan={9} className="px-3 py-6 text-center text-slate-400">
                          No sessions to show.
                        </td>
                      </tr>
                    )}
                    {displayRows.map((s) => (
                      <tr
                        key={s.row_index}
                        className={
                          s.status === "invalid"
                            ? "bg-red-50"
                            : s.status === "duplicate"
                            ? "bg-amber-50"
                            : ""
                        }
                      >
                        <td className="px-3 py-2 text-slate-400">{s.row_index}</td>
                        <td className="px-3 py-2">{s.parsed.date ?? "—"}</td>
                        <td className="px-3 py-2 whitespace-nowrap">
                          {s.parsed.start_time ?? "?"} – {s.parsed.end_time ?? "?"}
                        </td>
                        <td className="px-3 py-2 max-w-[160px] truncate" title={s.parsed.title}>
                          {s.parsed.title || <span className="text-slate-400 italic">missing</span>}
                        </td>
                        <td className="px-3 py-2">{s.parsed.subject || "—"}</td>
                        <td className="px-3 py-2 max-w-[120px] truncate" title={s.parsed.topic}>
                          {s.parsed.topic || "—"}
                        </td>
                        <td className="px-3 py-2">{s.parsed.subgroup_label || "—"}</td>
                        <td className="px-3 py-2">{s.parsed.requires_meet ? "Yes" : "No"}</td>
                        <td className="px-3 py-2">
                          <div className="flex flex-col gap-1">
                            <Badge status={s.status} />
                            {s.errors.map((err, i) => (
                              <span key={i} className="text-red-600 text-xs">{err}</span>
                            ))}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {commitError && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {commitError}
                </div>
              )}

              <div className="flex gap-3 pt-2">
                <button
                  onClick={() => { setStep(1); setPreview(null); }}
                  className="rounded-lg border border-slate-300 text-slate-600 px-4 py-2 text-sm hover:bg-slate-50"
                >
                  ← Back
                </button>
                {validSessions.length > 0 && (
                  <button
                    onClick={handleCommit}
                    disabled={committing}
                    className="rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 text-sm font-semibold disabled:opacity-60"
                  >
                    {committing
                      ? "Saving…"
                      : `Save ${validSessions.length} session${validSessions.length !== 1 ? "s" : ""} →`}
                  </button>
                )}
                {validSessions.length === 0 && (
                  <p className="text-sm text-amber-700 self-center">
                    No valid sessions to import. Fix the issues above or check the sheet layout.
                  </p>
                )}
              </div>
            </div>
          )}

          {/* ── STEP 3: Review & Publish ─────────────────────────────────── */}
          {step === 3 && commitResult && (
            <div className="space-y-6">
              <div className="rounded-lg bg-green-50 border border-green-200 p-5">
                <h2 className="font-semibold text-green-800 text-lg mb-3">
                  ✓ Import complete
                </h2>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <p className="text-green-700 font-medium">Sessions saved</p>
                    <p className="text-2xl font-bold text-green-800">{commitResult.created}</p>
                  </div>
                  <div>
                    <p className="text-amber-700 font-medium">Duplicates skipped</p>
                    <p className="text-2xl font-bold text-amber-800">{commitResult.skipped_duplicates}</p>
                  </div>
                  <div>
                    <p className="text-red-700 font-medium">Invalid rows</p>
                    <p className="text-2xl font-bold text-red-800">{commitResult.invalid_rows}</p>
                  </div>
                </div>
                <p className="text-xs text-green-700 mt-3">
                  Batch ID: #{commitResult.batch_id} · Status: {commitResult.status}
                </p>
              </div>

              {promoteResult ? (
                <div className="rounded-lg bg-teal-50 border border-teal-200 p-5">
                  <h3 className="font-semibold text-teal-800 mb-2">
                    ✓ {promoteResult.promoted} session{promoteResult.promoted !== 1 ? "s" : ""} promoted
                  </h3>
                  <p className="text-sm text-teal-700 mb-4">
                    Sessions are now in the publish pipeline. Head to the dashboard to generate Meet links and publish.
                  </p>
                  <button
                    onClick={goToDashboard}
                    className="rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 text-sm font-semibold"
                  >
                    Go to Classroom Dashboard →
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-slate-600">
                    Sessions are saved as drafts. Click below to promote them to live sessions
                    so you can generate Meet links and publish them from the dashboard.
                  </p>
                  <div className="flex gap-3">
                    <button
                      onClick={handlePromote}
                      disabled={promoting || commitResult.created === 0}
                      className="rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-5 py-2 text-sm font-semibold disabled:opacity-60"
                    >
                      {promoting
                        ? "Promoting…"
                        : `Promote ${commitResult.created} session${commitResult.created !== 1 ? "s" : ""} & Go to Classroom Dashboard`}
                    </button>
                    <button
                      onClick={goToDashboard}
                      className="rounded-lg border border-slate-300 text-slate-600 px-4 py-2 text-sm hover:bg-slate-50"
                    >
                      Skip — Go to Classroom Dashboard
                    </button>
                  </div>
                </div>
              )}

              <button
                onClick={() => {
                  setStep(1);
                  setPreview(null);
                  setCommitResult(null);
                  setPromoteResult(null);
                  setSheetUrl("");
                  setTargetDate("");
                  setTargetDay("");
                  setSheetName("");
                  setDefaultCourseId("");
                  setAvailableTabs([]);
                }}
                className="text-sm text-slate-500 hover:text-slate-700 underline"
              >
                Import another timetable
              </button>
            </div>
          )}
        </div>
      </div>
    </main>
  );
}

// ─── Helper component ────────────────────────────────────────────────────────

function SummaryCard({
  label,
  value,
  color = "slate",
}: {
  label: string;
  value: number;
  color?: "green" | "red" | "amber" | "slate";
}) {
  const colorMap: Record<string, string> = {
    green: "text-green-700",
    red: "text-red-700",
    amber: "text-amber-700",
    slate: "text-slate-700",
  };
  return (
    <div className="rounded-lg border border-slate-200 p-3 bg-slate-50">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-2xl font-bold ${colorMap[color]}`}>{value}</p>
    </div>
  );
}
