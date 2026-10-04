function resolveApiBase() {
  const raw = (process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (!raw || raw === "/") {
    return "/api";
  }

  const isLocalhost = /^https?:\/\/(localhost|127\.0\.0\.1)(:\d+)?(\/|$)/i.test(raw);
  if (isLocalhost) {
    return "/api";
  }

  return raw.endsWith("/") ? raw.slice(0, -1) : raw;
}

const API_URL = resolveApiBase();

export class ApiError extends Error {
  status: number;
  code?: string;
  feature?: string;
  missingScopes?: string[];
  reauthorizeUrl?: string;
  reconnectFlow?: string;

  constructor(message: string, options: {
    status: number;
    code?: string;
    feature?: string;
    missingScopes?: string[];
    reauthorizeUrl?: string;
    reconnectFlow?: string;
  }) {
    super(message);
    this.status = options.status;
    this.code = options.code;
    this.feature = options.feature;
    this.missingScopes = options.missingScopes;
    this.reauthorizeUrl = options.reauthorizeUrl;
    this.reconnectFlow = options.reconnectFlow;
  }
}

export function isGoogleScopeMissingError(error: unknown): error is ApiError {
  return error instanceof ApiError && error.code === "GOOGLE_SCOPE_MISSING";
}

async function buildError(response: Response) {
  let message = `Request failed: ${response.status}`;
  let code: string | undefined;
  let feature: string | undefined;
  let missingScopes: string[] | undefined;
  let reauthorizeUrl: string | undefined;
  let reconnectFlow: string | undefined;
  try {
    const data = await response.json();
    if (typeof data?.detail === "string" && data.detail.trim()) {
      message = data.detail;
    } else if (typeof data?.message === "string" && data.message.trim()) {
      message = data.message;
    } else if (Array.isArray(data?.errors) && data.errors.length > 0) {
      message = data.errors.join("\n");
    }
    code = typeof data?.code === "string" ? data.code : undefined;
    feature = typeof data?.feature === "string" ? data.feature : undefined;
    missingScopes = Array.isArray(data?.missingScopes)
      ? data.missingScopes.filter((scope: unknown): scope is string => typeof scope === "string")
      : undefined;
    reauthorizeUrl = typeof data?.reauthorizeUrl === "string" ? data.reauthorizeUrl : undefined;
    reconnectFlow = typeof data?.reconnectFlow === "string" ? data.reconnectFlow : undefined;
  } catch {
    // Ignore non-JSON error bodies.
  }
  return new ApiError(message, {
    status: response.status,
    code,
    feature,
    missingScopes,
    reauthorizeUrl,
    reconnectFlow,
  });
}

async function req(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw await buildError(response);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function reqForm(path: string, body: FormData, init: RequestInit = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    method: init.method || "POST",
    body,
    credentials: "include",
    cache: "no-store",
  });

  if (!response.ok) {
    throw await buildError(response);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

async function reqBlob(path: string, init: RequestInit = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    credentials: "include",
    cache: "no-store",
  });
  if (!response.ok) {
    throw await buildError(response);
  }
  return response.blob();
}

export const api = {
  authStatus: () => req("/auth/status"),
  authStart: (options?: { mode?: "default" | "reconnect" | "upgrade"; upgrade?: string }) => {
    const params = new URLSearchParams();
    if (options?.mode) {
      params.set("mode", options.mode);
    }
    if (options?.upgrade) {
      params.set("upgrade", options.upgrade);
    }
    const query = params.toString();
    return req(`/auth/google/start${query ? `?${query}` : ""}`);
  },
  logout: () => req("/auth/logout", { method: "POST" }),
  courses: () => req("/classrooms/"),
  syncCourses: () => req("/classrooms/sync/"),
  sessions: () => req("/sessions/"),
  createSession: (payload: Record<string, unknown>) =>
    req("/sessions/", { method: "POST", body: JSON.stringify(payload) }),
  updateSession: (id: number, payload: Record<string, unknown>) =>
    req(`/sessions/${id}/`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteSession: (id: number) => req(`/sessions/${id}/`, { method: "DELETE" }),
  generateMeet: (session_ids: number[]) =>
    req("/sessions/generate-meet/", { method: "POST", body: JSON.stringify({ session_ids }) }),
  schedulePosts: (session_ids: number[]) =>
    req("/sessions/schedule-posts/", { method: "POST", body: JSON.stringify({ session_ids }) }),
  publishNow: (session_ids: number[]) =>
    req("/sessions/publish-now/", { method: "POST", body: JSON.stringify({ session_ids }) }),
  logs: () => req("/logs/"),
  // Import
  previewSheetImport: (payload: Record<string, unknown>) =>
    req("/imports/google-sheet/preview", { method: "POST", body: JSON.stringify(payload) }),
  previewFileImport: (file: File, fields: Record<string, string>) => {
    const form = new FormData();
    form.append("file", file);
    Object.entries(fields).forEach(([key, value]) => {
      if (value !== "") form.append(key, value);
    });
    return reqForm("/imports/file/preview", form);
  },
  commitSheetImport: (payload: Record<string, unknown>) =>
    req("/imports/google-sheet/commit", { method: "POST", body: JSON.stringify(payload) }),
  listImportBatches: () => req("/imports/"),
  getImportBatch: (id: number) => req(`/imports/${id}/`),
  promoteImportBatch: (id: number) =>
    req(`/imports/${id}/promote/`, { method: "POST" }),
  // Combined-day message
  combinedDayPreview: (payload: Record<string, unknown>) =>
    req("/publish/combined-day-preview", { method: "POST", body: JSON.stringify(payload) }),
  combinedDayPublish: (payload: Record<string, unknown>) =>
    req("/publish/combined-day-post", { method: "POST", body: JSON.stringify(payload) }),

  // Phase 2 — Groups
  listGroups: () => req("/groups"),
  syncGroups: (domain?: string) =>
    req("/groups/sync", { method: "POST", body: JSON.stringify({ domain }) }),
  addMemberToGroup: (group_email: string, user_email: string) =>
    req("/groups/add-member", { method: "POST", body: JSON.stringify({ group_email, user_email }) }),
  removeMemberFromGroup: (group_email: string, user_email: string) =>
    req("/groups/remove-member", { method: "POST", body: JSON.stringify({ group_email, user_email }) }),
  groupMembers: (group_email: string) =>
    req(`/groups/${encodeURIComponent(group_email)}/members`),

  // Phase 2 — Classroom Admin
  adminCourses: () => req("/classroom/courses"),
  classroomRoster: (course_id: string) =>
    req(`/classroom/courses/${encodeURIComponent(course_id)}/roster`),
  addStudent: (course_id: string, student_email: string) =>
    req("/classroom/add-student", { method: "POST", body: JSON.stringify({ course_id, student_email }) }),
  addTeacher: (course_id: string, teacher_email: string) =>
    req("/classroom/add-teacher", { method: "POST", body: JSON.stringify({ course_id, teacher_email }) }),

  // Phase 2 — Bundles
  listBundles: (active_only?: boolean) =>
    req(`/bundles${active_only ? "?active_only=true" : ""}`),
  createBundle: (payload: Record<string, unknown>) =>
    req("/bundles/create", { method: "POST", body: JSON.stringify(payload) }),
  updateBundle: (id: number, payload: Record<string, unknown>) =>
    req(`/bundles/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteBundle: (id: number) =>
    req(`/bundles/${id}/delete`, { method: "DELETE" }),

  // Phase 2 — Commands
  commandPreview: (command_type: string, params: Record<string, unknown>) =>
    req("/commands/preview", { method: "POST", body: JSON.stringify({ command_type, params }) }),
  commandRun: (command_type: string, params: Record<string, unknown>, dry_run = false) =>
    req("/commands/run", { method: "POST", body: JSON.stringify({ command_type, params, dry_run }) }),
  listJobs: () => req("/commands/jobs"),
  getJob: (id: number) => req(`/commands/jobs/${id}`),
  commandLogs: () => req("/commands/logs"),
  retryJob: (job_id: number) =>
    req("/commands/retry", { method: "POST", body: JSON.stringify({ job_id }) }),

  // Phase 2 — CSV Import
  csvPreview: (csv_text: string, default_bundle_id?: number) =>
    req("/commands/import/csv/preview", {
      method: "POST",
      body: JSON.stringify({ csv_text, default_bundle_id }),
    }),
  csvRun: (csv_text: string, default_bundle_id?: number, dry_run = false) =>
    req("/commands/import/csv/run", {
      method: "POST",
      body: JSON.stringify({ csv_text, default_bundle_id, dry_run }),
    }),

  // Module B — Directory operations
  listDirectoryUsers: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params || {}).toString();
    return req(`/directory/users${q ? `?${q}` : ""}`);
  },
  getDirectoryUser: (id: number) => req(`/directory/users/${id}`),
  updateDirectoryUser: (id: number, payload: Record<string, unknown>) =>
    req(`/directory/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  syncDirectory: (payload: Record<string, unknown> = {}) =>
    req("/directory/sync", { method: "POST", body: JSON.stringify(payload) }),
  directoryStats: () => req("/directory/stats"),
  listDirectorySyncJobs: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params || {}).toString();
    return req(`/directory/sync-jobs${q ? `?${q}` : ""}`);
  },
  getDirectorySyncJob: (id: number) => req(`/directory/sync-jobs/${id}`),

  listDirectoryIssues: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params || {}).toString();
    return req(`/directory/issues${q ? `?${q}` : ""}`);
  },
  getDirectoryIssue: (id: number) => req(`/directory/issues/${id}`),
  scanDirectoryIssues: (payload: Record<string, unknown> = {}) =>
    req("/directory/issues/scan", { method: "POST", body: JSON.stringify(payload) }),
  approveDirectoryIssue: (id: number, note = "") =>
    req(`/directory/issues/${id}/approve`, { method: "POST", body: JSON.stringify({ note }) }),
  rejectDirectoryIssue: (id: number, note = "") =>
    req(`/directory/issues/${id}/reject`, { method: "POST", body: JSON.stringify({ note }) }),
  markDirectoryIssueException: (id: number, note = "") =>
    req(`/directory/issues/${id}/mark-exception`, { method: "POST", body: JSON.stringify({ note }) }),
  bulkApproveDirectoryIssues: (issue_ids: number[], note = "") =>
    req("/directory/issues/bulk-approve", { method: "POST", body: JSON.stringify({ issue_ids, note }) }),

  listOuTemplates: () => req("/org-units/templates"),
  createOuTemplate: (payload: Record<string, unknown>) =>
    req("/org-units/templates", { method: "POST", body: JSON.stringify(payload) }),
  updateOuTemplate: (id: number, payload: Record<string, unknown>) =>
    req(`/org-units/templates/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  listEmailTemplates: () => req("/email-templates"),
  createEmailTemplate: (payload: Record<string, unknown>) =>
    req("/email-templates", { method: "POST", body: JSON.stringify(payload) }),
  updateEmailTemplate: (id: number, payload: Record<string, unknown>) =>
    req(`/email-templates/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  previewDirectoryChangeJob: (payload: Record<string, unknown>) =>
    req("/directory/change-jobs/preview", { method: "POST", body: JSON.stringify(payload) }),
  executeDirectoryChangeJob: (payload: Record<string, unknown>) =>
    req("/directory/change-jobs/execute", { method: "POST", body: JSON.stringify(payload) }),
  listDirectoryChangeJobs: () => req("/directory/change-jobs"),
  getDirectoryChangeJob: (id: number) => req(`/directory/change-jobs/${id}`),
  listDirectoryApprovalRequests: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params || {}).toString();
    return req(`/directory/approvals${q ? `?${q}` : ""}`);
  },
  createDirectoryApprovalRequest: (payload: Record<string, unknown>) =>
    req("/directory/approvals", { method: "POST", body: JSON.stringify(payload) }),
  getDirectoryApprovalRequest: (id: number) => req(`/directory/approvals/${id}`),
  approveDirectoryApprovalRequest: (id: number, review_notes = "") =>
    req(`/directory/approvals/${id}/approve`, { method: "POST", body: JSON.stringify({ review_notes }) }),
  rejectDirectoryApprovalRequest: (id: number, review_notes = "") =>
    req(`/directory/approvals/${id}/reject`, { method: "POST", body: JSON.stringify({ review_notes }) }),
  cancelDirectoryApprovalRequest: (id: number, review_notes = "") =>
    req(`/directory/approvals/${id}/cancel`, { method: "POST", body: JSON.stringify({ review_notes }) }),

  provisioningPreview: (payload: Record<string, unknown>) =>
    req("/provisioning/preview", { method: "POST", body: JSON.stringify(payload) }),
  provisioningCreate: (payload: Record<string, unknown>) =>
    req("/provisioning/create", { method: "POST", body: JSON.stringify(payload) }),
  provisioningBulkPreview: (rows: Record<string, unknown>[]) =>
    req("/provisioning/bulk-preview", { method: "POST", body: JSON.stringify({ rows }) }),
  provisioningBulkCreate: (preview_record_ids: number[], approval_request_id?: number) =>
    req("/provisioning/bulk-create", {
      method: "POST",
      body: JSON.stringify({ preview_record_ids, approval_request_id }),
    }),
  listProvisioningRecords: () => req("/provisioning/records"),
  getProvisioningRecord: (id: number) => req(`/provisioning/records/${id}`),

  listDirectoryAuditLogs: () => req("/directory/audit-logs"),
  getDirectoryAuditLog: (id: number) => req(`/directory/audit-logs/${id}`),
  verifyDirectoryUpload: (file: File, options?: { mapping?: Record<string, string>; sheet_name?: string }) => {
    const form = new FormData();
    form.append("file", file);
    if (options?.sheet_name) {
      form.append("sheet_name", options.sheet_name);
    }
    if (options?.mapping) {
      form.append("mapping", JSON.stringify(options.mapping));
    }
    return reqForm("/directory/verify-upload", form);
  },
  listDirectoryVerifyJobs: (params?: Record<string, string>) => {
    const q = new URLSearchParams(params || {}).toString();
    return req(`/directory/verify-jobs${q ? `?${q}` : ""}`);
  },
  getDirectoryVerifyJob: (id: number) => req(`/directory/verify-jobs/${id}`),
  listDirectoryVerifyRows: (id: number, params?: Record<string, string>) => {
    const q = new URLSearchParams(params || {}).toString();
    return req(`/directory/verify-jobs/${id}/rows${q ? `?${q}` : ""}`);
  },
  exportDirectoryVerifyJob: (id: number, format: "csv" | "xlsx" = "csv") =>
    reqBlob(`/directory/verify-jobs/${id}/export?file_format=${format}`),
};

// Phase 2B — Classroom Lifecycle + Direct Removal
export const phase2bApi = {
  classroomPreflight: (action: string, params: Record<string, string>) =>
    req("/classroom/preflight", {
      method: "POST",
      body: JSON.stringify({ action, ...params }),
    }),
  createCourse: (data: {
    name: string;
    section?: string;
    description_heading?: string;
    description?: string;
    room?: string;
    owner_id?: string;
  }) =>
    req("/classroom/courses/create", {
      method: "POST",
      body: JSON.stringify(data),
    }),
  archiveCourse: (course_id: string) =>
    req(`/classroom/courses/${course_id}/archive`, { method: "POST" }),
  deleteCourse: (course_id: string) =>
    req(`/classroom/courses/${course_id}`, { method: "DELETE" }),
  removeStudent: (course_id: string, student_email: string) =>
    req("/classroom/remove-student", {
      method: "POST",
      body: JSON.stringify({ course_id, student_email }),
    }),
  removeTeacher: (course_id: string, teacher_email: string) =>
    req("/classroom/remove-teacher", {
      method: "POST",
      body: JSON.stringify({ course_id, teacher_email }),
    }),
};
