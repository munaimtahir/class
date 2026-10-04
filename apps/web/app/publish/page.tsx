"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

type Course = { id: number; google_course_id: string; name: string; section: string };

type Session = {
  id: number;
  course: number;
  date: string;
  start_time: string;
  end_time: string;
  title: string;
  subject: string;
  group: string;
  meet_link: string;
  status: string;
};

type PreviewResult = {
  template: string;
  session_count: number;
  skipped_count: number;
  warnings: { session_id: number; title: string; warning: string }[];
  skipped: { session_id: number; reason: string }[];
  message: string;
};

type PublishResult = {
  google_post_id: string;
  posting_mode: string;
  session_count: number;
  message_length: number;
};

type Options = {
  include_year: boolean;
  include_video_label: boolean;
  sort_by_time: boolean;
  include_day_heading: boolean;
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function groupByDate(sessions: Session[]): Record<string, Session[]> {
  return sessions.reduce<Record<string, Session[]>>((acc, s) => {
    (acc[s.date] = acc[s.date] || []).push(s);
    return acc;
  }, {});
}

function formatDateLabel(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return d.toLocaleDateString("en-US", { weekday: "long", month: "long", day: "numeric" });
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function PublishPage() {
  const router = useRouter();

  const [courses, setCourses] = useState<Course[]>([]);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loading, setLoading] = useState(true);

  // Selection
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());
  const [targetCourseId, setTargetCourseId] = useState("");

  // Options
  const [options, setOptions] = useState<Options>({
    include_year: false,
    include_video_label: true,
    sort_by_time: true,
    include_day_heading: false,
  });

  // Preview state
  const [preview, setPreview] = useState<PreviewResult | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  // Publish state
  const [publishing, setPublishing] = useState(false);
  const [publishResult, setPublishResult] = useState<PublishResult | null>(null);
  const [publishError, setPublishError] = useState("");

  useEffect(() => {
    Promise.all([api.courses(), api.sessions()])
      .then(([c, s]) => {
        setCourses(c);
        setSessions(s);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  // Auto-regenerate preview whenever selection or options change
  const generatePreview = useCallback(async (ids: number[], opts: Options) => {
    if (ids.length === 0) {
      setPreview(null);
      return;
    }
    setPreviewLoading(true);
    setPreviewError("");
    try {
      const result: PreviewResult = await api.combinedDayPreview({
        session_ids: ids,
        template: "single_day_combined_message",
        options: opts,
      });
      setPreview(result);
    } catch (err: unknown) {
      setPreviewError(err instanceof Error ? err.message : "Preview failed.");
      setPreview(null);
    } finally {
      setPreviewLoading(false);
    }
  }, []);

  function handleToggleSession(id: number) {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    setSelectedIds(next);
    generatePreview(Array.from(next), options);
  }

  function handleSelectDate(date: string) {
    const dateIds = sessions.filter((s) => s.date === date).map((s) => s.id);
    const allSelected = dateIds.every((id) => selectedIds.has(id));
    const next = new Set(selectedIds);
    dateIds.forEach((id) => (allSelected ? next.delete(id) : next.add(id)));
    setSelectedIds(next);
    generatePreview(Array.from(next), options);
  }

  function handleOptionChange<K extends keyof Options>(key: K, value: Options[K]) {
    const next = { ...options, [key]: value };
    setOptions(next);
    generatePreview(Array.from(selectedIds), next);
  }

  async function handlePublish() {
    if (!targetCourseId) {
      setPublishError("Please select a destination course.");
      return;
    }
    if (selectedIds.size === 0) {
      setPublishError("No sessions selected.");
      return;
    }
    const course = courses.find((c) => String(c.id) === targetCourseId);
    if (!course) {
      setPublishError("Course not found.");
      return;
    }
    setPublishing(true);
    setPublishError("");
    setPublishResult(null);
    try {
      const result: PublishResult = await api.combinedDayPublish({
        session_ids: Array.from(selectedIds),
        course_id: course.google_course_id,
        template: "single_day_combined_message",
        options,
      });
      setPublishResult(result);
    } catch (err: unknown) {
      setPublishError(err instanceof Error ? err.message : "Publish failed.");
    } finally {
      setPublishing(false);
    }
  }

  const byDate = groupByDate(sessions);
  const sortedDates = Object.keys(byDate).sort();

  return (
    <main className="min-h-screen bg-gradient-to-br from-teal-50 via-white to-amber-50 p-6">
      <div className="max-w-6xl mx-auto space-y-6">

        {/* Header */}
        <header className="rounded-xl bg-white p-5 shadow border border-slate-200 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">Post Day Timetable</h1>
            <p className="text-sm text-slate-500 mt-1">
              Generate one combined Classroom announcement for an entire day's sessions.
            </p>
          </div>
          <button onClick={() => router.push("/classroom/dashboard")} className="text-sm text-teal-700 hover:underline">
            ← Classroom Dashboard
          </button>
        </header>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Left column — session picker + options */}
          <div className="space-y-6">

            {/* Session selector */}
            <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
              <h2 className="font-semibold text-slate-800 mb-3">
                1. Select sessions
                {selectedIds.size > 0 && (
                  <span className="ml-2 text-teal-600 text-sm font-normal">
                    ({selectedIds.size} selected)
                  </span>
                )}
              </h2>

              {loading ? (
                <p className="text-sm text-slate-400">Loading sessions…</p>
              ) : sortedDates.length === 0 ? (
                <p className="text-sm text-slate-400">
                  No sessions found.{" "}
                  <a href="/imports" className="text-teal-600 underline">Import one</a>.
                </p>
              ) : (
                <div className="space-y-4 max-h-[480px] overflow-y-auto pr-1">
                  {sortedDates.map((d) => {
                    const daySessions = byDate[d];
                    const dayIds = daySessions.map((s) => s.id);
                    const allChecked = dayIds.every((id) => selectedIds.has(id));
                    const someChecked = dayIds.some((id) => selectedIds.has(id));
                    return (
                      <div key={d}>
                        {/* Date header row */}
                        <label className="flex items-center gap-2 cursor-pointer mb-1">
                          <input
                            type="checkbox"
                            checked={allChecked}
                            ref={(el) => {
                              if (el) el.indeterminate = !allChecked && someChecked;
                            }}
                            onChange={() => handleSelectDate(d)}
                            className="accent-teal-600 w-4 h-4"
                          />
                          <span className="text-sm font-semibold text-slate-700">
                            {formatDateLabel(d)}
                          </span>
                          <span className="text-xs text-slate-400">({daySessions.length})</span>
                        </label>

                        {/* Individual session rows */}
                        <div className="ml-6 space-y-1">
                          {daySessions.map((s) => (
                            <label
                              key={s.id}
                              className="flex items-center gap-2 cursor-pointer group"
                            >
                              <input
                                type="checkbox"
                                checked={selectedIds.has(s.id)}
                                onChange={() => handleToggleSession(s.id)}
                                className="accent-teal-600 w-4 h-4"
                              />
                              <span className="text-sm text-slate-700 group-hover:text-teal-700 flex-1 min-w-0 truncate">
                                {s.title || <em className="text-slate-400">untitled</em>}
                              </span>
                              <span className="text-xs text-slate-400 whitespace-nowrap">
                                {s.start_time.slice(0, 5)}
                              </span>
                              {s.meet_link ? (
                                <span className="text-xs text-green-600">●</span>
                              ) : (
                                <span className="text-xs text-amber-500" title="No meet link">○</span>
                              )}
                            </label>
                          ))}
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {/* Options panel */}
            <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
              <h2 className="font-semibold text-slate-800 mb-3">2. Template options</h2>
              <div className="space-y-2 text-sm">
                <Toggle
                  label="Sort by start time"
                  checked={options.sort_by_time}
                  onChange={(v) => handleOptionChange("sort_by_time", v)}
                />
                <Toggle
                  label="Include 'Video call link:' label"
                  checked={options.include_video_label}
                  onChange={(v) => handleOptionChange("include_video_label", v)}
                />
                <Toggle
                  label="Day heading at top (e.g. 'Tuesday timetable — March 10')"
                  checked={options.include_day_heading}
                  onChange={(v) => handleOptionChange("include_day_heading", v)}
                />
                <Toggle
                  label="Include year in date line"
                  checked={options.include_year}
                  onChange={(v) => handleOptionChange("include_year", v)}
                />
              </div>
            </section>

            {/* Destination + publish */}
            <section className="rounded-xl bg-white p-5 shadow border border-slate-200">
              <h2 className="font-semibold text-slate-800 mb-3">3. Publish destination</h2>

              <select
                value={targetCourseId}
                onChange={(e) => setTargetCourseId(e.target.value)}
                className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-teal-400 mb-4"
              >
                <option value="">— select course —</option>
                {courses.map((c) => (
                  <option key={c.id} value={String(c.id)}>
                    {c.name} {c.section ? `(${c.section})` : ""}
                  </option>
                ))}
              </select>

              {publishError && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-2 text-sm text-red-700 mb-3">
                  {publishError}
                </div>
              )}

              {publishResult ? (
                <div className="rounded-lg bg-green-50 border border-green-200 p-4 text-sm">
                  <p className="font-semibold text-green-800 mb-1">✓ Published!</p>
                  <p className="text-green-700">
                    {publishResult.session_count} session{publishResult.session_count !== 1 ? "s" : ""}{" "}
                    combined into one announcement ({publishResult.message_length} characters).
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    Post ID: {publishResult.google_post_id}
                  </p>
                  <button
                    onClick={() => {
                      setPublishResult(null);
                      setSelectedIds(new Set());
                      setPreview(null);
                    }}
                    className="mt-3 text-teal-600 underline text-xs"
                  >
                    Post another day
                  </button>
                </div>
              ) : (
                <button
                  onClick={handlePublish}
                  disabled={publishing || selectedIds.size === 0 || !targetCourseId || !preview?.message}
                  className="w-full rounded-lg bg-teal-600 hover:bg-teal-700 text-white px-5 py-2.5 text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {publishing
                    ? "Publishing…"
                    : `Publish ${selectedIds.size} session${selectedIds.size !== 1 ? "s" : ""} as one message`}
                </button>
              )}
            </section>
          </div>

          {/* Right column — live preview */}
          <div className="space-y-4">
            <section className="rounded-xl bg-white p-5 shadow border border-slate-200 sticky top-6">
              <div className="flex items-center justify-between mb-3">
                <h2 className="font-semibold text-slate-800">Live preview</h2>
                {preview && (
                  <div className="flex items-center gap-3 text-xs text-slate-500">
                    <span className="text-green-700 font-medium">
                      {preview.session_count} session{preview.session_count !== 1 ? "s" : ""}
                    </span>
                    {preview.skipped_count > 0 && (
                      <span className="text-amber-600">{preview.skipped_count} skipped</span>
                    )}
                    {preview.warnings.length > 0 && (
                      <span className="text-orange-600">{preview.warnings.length} warning{preview.warnings.length !== 1 ? "s" : ""}</span>
                    )}
                  </div>
                )}
              </div>

              {previewLoading && (
                <div className="flex items-center gap-2 py-12 justify-center text-slate-400 text-sm">
                  <span className="animate-spin text-teal-500">⟳</span> Generating preview…
                </div>
              )}

              {previewError && !previewLoading && (
                <div className="rounded-lg bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-700">
                  {previewError}
                </div>
              )}

              {!previewLoading && !previewError && !preview && (
                <div className="py-12 text-center text-slate-400 text-sm">
                  Select sessions on the left to see the preview.
                </div>
              )}

              {!previewLoading && preview && (
                <>
                  {/* Warnings */}
                  {preview.warnings.length > 0 && (
                    <div className="rounded-lg bg-amber-50 border border-amber-200 px-4 py-2 text-xs text-amber-800 mb-3 space-y-1">
                      {preview.warnings.map((w) => (
                        <p key={w.session_id}>⚠ {w.title}: {w.warning}</p>
                      ))}
                    </div>
                  )}

                  {/* Skipped */}
                  {preview.skipped.length > 0 && (
                    <div className="rounded-lg bg-slate-50 border border-slate-200 px-4 py-2 text-xs text-slate-600 mb-3 space-y-1">
                      {preview.skipped.map((sk, i) => (
                        <p key={i}>Skipped session #{sk.session_id}: {sk.reason}</p>
                      ))}
                    </div>
                  )}

                  {/* Message preview */}
                  <div className="relative">
                    <pre className="whitespace-pre-wrap font-mono text-sm text-slate-800 bg-slate-50 rounded-lg border border-slate-200 p-4 max-h-[560px] overflow-y-auto leading-relaxed">
                      {preview.message}
                    </pre>
                    <button
                      onClick={() => navigator.clipboard.writeText(preview.message)}
                      className="absolute top-2 right-2 text-xs rounded bg-white border border-slate-200 px-2 py-1 text-slate-500 hover:text-teal-700 hover:border-teal-300"
                      title="Copy to clipboard"
                    >
                      Copy
                    </button>
                  </div>

                  <p className="text-xs text-slate-400 mt-2 text-right">
                    {preview.message.length} characters
                    {preview.message.length > 3000 && (
                      <span className="text-amber-600 ml-1">
                        · long message — verify Classroom API limit
                      </span>
                    )}
                  </p>
                </>
              )}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}

// ─── Toggle helper ────────────────────────────────────────────────────────────

function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-center gap-3 cursor-pointer select-none">
      <button
        type="button"
        role="switch"
        aria-checked={checked}
        onClick={() => onChange(!checked)}
        className={`relative inline-flex h-5 w-9 items-center rounded-full transition-colors ${
          checked ? "bg-teal-500" : "bg-slate-300"
        }`}
      >
        <span
          className={`inline-block h-3.5 w-3.5 transform rounded-full bg-white shadow transition-transform ${
            checked ? "translate-x-4.5" : "translate-x-0.5"
          }`}
        />
      </button>
      <span className="text-slate-700">{label}</span>
    </label>
  );
}
