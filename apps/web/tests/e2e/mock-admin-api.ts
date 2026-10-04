import { Page, Route } from "@playwright/test";

// ─── Types ────────────────────────────────────────────────────────────────────

export type MockGroup = {
  id: number;
  external_id: string;
  email: string;
  display_name: string;
  metadata_json: Record<string, unknown>;
  synced_at: string | null;
};

export type MockAdminCourse = {
  id: string;
  name: string;
  section: string;
  courseState: string;
  alternateLink: string;
  ownerId: string;
};

export type MockBundle = {
  id: number;
  name: string;
  role_type: string;
  groups_json: string[];
  classroom_courses_json: string[];
  description: string;
  active: boolean;
  created_by: string | null;
};

export type MockJob = {
  id: number;
  job_type: string;
  created_by_email: string | null;
  status: string;
  dry_run: boolean;
  item_count: number;
  target_summary_json: Record<string, unknown>;
  result_summary_json: Record<string, unknown>;
  created_at: string;
};

export type MockDirectoryUser = {
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

export type MockDirectoryIssue = {
  id: number;
  directory_user: number | null;
  directory_user_email: string | null;
  issue_type: string;
  severity: "critical" | "warning" | "info";
  status: string;
  actual_value: string;
  expected_value: string;
  suggested_action: string;
  detected_at: string;
};

export type MockDirectoryChangeJob = {
  id: number;
  job_type: string;
  scope_type: string;
  status: string;
  is_dry_run: boolean;
  item_count: number;
  preview_summary: Record<string, unknown>;
  execution_summary: Record<string, unknown>;
  items?: Array<{
    id: number;
    issue: number | null;
    action: string;
    before_value: string;
    after_value: string;
    status: string;
    error_text?: string;
    result_json?: Record<string, unknown>;
  }>;
  created_at: string;
};

export type MockProvisioningRecord = {
  id: number;
  full_name: string;
  user_category: string;
  generated_email: string;
  target_org_unit_path: string;
  status: string;
  failure_reason: string;
  created_at: string;
};

export type MockOuTemplate = {
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

export type MockEmailRule = {
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

export type MockDirectoryAuditLog = {
  id: number;
  actor_email: string | null;
  action_type: string;
  target_ref: string;
  is_dry_run: boolean;
  success: boolean;
  error_message: string;
  created_at: string;
};

export type MockApprovalRequest = {
  id: number;
  action_type: string;
  target_type: string;
  target_reference: string;
  payload: Record<string, unknown>;
  requested_by_email: string | null;
  requested_at: string;
  status: string;
  reviewed_by_email: string | null;
  reviewed_at: string | null;
  review_notes: string;
  execution_status: string;
  execution_message: string;
  linked_change_job: number | null;
  linked_provisioning_record: number | null;
  created_at: string;
  updated_at: string;
};

export type MockDirectorySyncJob = {
  id: number;
  status: string;
  completed_at: string | null;
  pages_fetched: number;
  users_fetched_total: number;
  users_upserted_total: number;
  users_created_total: number;
  users_updated_total: number;
  error_message: string;
  created_at: string;
};

export type MockDirectoryVerifyJob = {
  id: number;
  source_filename: string;
  source_type: string;
  sheet_name: string;
  status: string;
  row_count: number;
  summary_json: Record<string, number>;
  column_mapping_json: Record<string, string>;
  created_at: string;
  completed_at: string | null;
};

export type MockDirectoryVerifyRow = {
  id: number;
  job: number;
  row_no: number;
  input_json: Record<string, string>;
  matched_email: string;
  matched_name: string;
  match_basis: string;
  verdict: string;
  notes: string;
};

type AdminMockOptions = {
  authenticated?: boolean;
  userEmail?: string;
  groups?: MockGroup[];
  adminCourses?: MockAdminCourse[];
  bundles?: MockBundle[];
  jobs?: MockJob[];
  directoryUsers?: MockDirectoryUser[];
  directoryIssues?: MockDirectoryIssue[];
  directoryChangeJobs?: MockDirectoryChangeJob[];
  provisioningRecords?: MockProvisioningRecord[];
  ouTemplates?: MockOuTemplate[];
  emailRules?: MockEmailRule[];
  directoryAuditLogs?: MockDirectoryAuditLog[];
  approvalRequests?: MockApprovalRequest[];
  directorySyncJobs?: MockDirectorySyncJob[];
  directoryVerifyJobs?: MockDirectoryVerifyJob[];
  directoryVerifyRows?: MockDirectoryVerifyRow[];
  classroomCoursesError?: { status: number; body: Record<string, unknown> };
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

const DEFAULT_GROUPS: MockGroup[] = [
  { id: 1, external_id: "grp-1", email: "year1@school.org", display_name: "Year 1 Students", metadata_json: { directMembersCount: "42" }, synced_at: "2024-03-01T10:00:00Z" },
  { id: 2, external_id: "grp-2", email: "staff@school.org", display_name: "Teaching Staff", metadata_json: { directMembersCount: "12" }, synced_at: "2024-03-01T10:00:00Z" },
];

const DEFAULT_ADMIN_COURSES: MockAdminCourse[] = [
  { id: "c-101", name: "Anatomy I", section: "A", courseState: "ACTIVE", alternateLink: "https://classroom.google.com/c/c-101", ownerId: "owner@school.org" },
  { id: "c-102", name: "Physiology II", section: "B", courseState: "ACTIVE", alternateLink: "https://classroom.google.com/c/c-102", ownerId: "owner@school.org" },
  { id: "c-103", name: "Archived Course", section: "", courseState: "ARCHIVED", alternateLink: "https://classroom.google.com/c/c-103", ownerId: "owner@school.org" },
];

const DEFAULT_BUNDLES: MockBundle[] = [
  { id: 1, name: "Year 1 Onboarding", role_type: "student", groups_json: ["year1@school.org"], classroom_courses_json: ["c-101"], description: "Bundle for new Year 1 students", active: true, created_by: "admin@school.org" },
];

const DEFAULT_JOBS: MockJob[] = [
  { id: 1, job_type: "ADD_STUDENT_TO_COURSE", created_by_email: "admin@school.org", status: "completed", dry_run: false, item_count: 3, target_summary_json: { course: "c-101" }, result_summary_json: { success: 3, failed: 0, skipped: 0 }, created_at: "2024-03-10T09:00:00Z" },
  { id: 2, job_type: "REMOVE_STUDENT_FROM_COURSE", created_by_email: "admin@school.org", status: "partial", dry_run: false, item_count: 2, target_summary_json: { course: "c-102" }, result_summary_json: { success: 1, failed: 1, skipped: 0 }, created_at: "2024-03-11T09:00:00Z" },
];

const DEFAULT_DIRECTORY_USERS: MockDirectoryUser[] = [
  {
    id: 1,
    primary_email: "alice.brown@school.org",
    full_name: "Alice Brown",
    user_category: "student",
    org_unit_path: "/Students/Legacy",
    expected_org_unit_path: "/Students/MBBS/2026",
    expected_email_valid: false,
    external_identifier: "1001",
    suspended: false,
    archived: false,
    last_synced_at: "2024-03-15T09:00:00Z",
  },
  {
    id: 2,
    primary_email: "dr.khan@school.org",
    full_name: "Dr Khan",
    user_category: "faculty",
    org_unit_path: "/Faculty/Medicine",
    expected_org_unit_path: "/Faculty/Medicine",
    expected_email_valid: true,
    external_identifier: "F-200",
    suspended: false,
    archived: false,
    last_synced_at: "2024-03-15T09:00:00Z",
  },
];

const DEFAULT_DIRECTORY_ISSUES: MockDirectoryIssue[] = [
  {
    id: 1,
    directory_user: 1,
    directory_user_email: "alice.brown@school.org",
    issue_type: "invalid_org_unit",
    severity: "warning",
    status: "detected",
    actual_value: "/Students/Legacy",
    expected_value: "/Students/MBBS/2026",
    suggested_action: "move_ou",
    detected_at: "2024-03-15T09:15:00Z",
  },
];

const DEFAULT_DIRECTORY_CHANGE_JOBS: MockDirectoryChangeJob[] = [
  {
    id: 1,
    job_type: "ou_correction",
    scope_type: "issue_selection",
    status: "preview_ready",
    is_dry_run: true,
    item_count: 1,
    preview_summary: { items: 1 },
    execution_summary: {},
    created_at: "2024-03-15T09:20:00Z",
  },
];

const DEFAULT_PROVISIONING_RECORDS: MockProvisioningRecord[] = [
  {
    id: 1,
    full_name: "New Student",
    user_category: "student",
    generated_email: "new.student@school.org",
    target_org_unit_path: "/Students/MBBS/2027",
    status: "previewed",
    failure_reason: "",
    created_at: "2024-03-15T09:25:00Z",
  },
];

const DEFAULT_OU_TEMPLATES: MockOuTemplate[] = [
  {
    id: 1,
    name: "MBBS 2026",
    user_category: "student",
    department: "Medicine",
    program: "MBBS",
    batch: "2026",
    year: "",
    target_org_unit_path: "/Students/MBBS/2026",
    priority: 10,
    is_active: true,
  },
];

const DEFAULT_EMAIL_RULES: MockEmailRule[] = [
  {
    id: 1,
    name: "Student pattern",
    user_category: "student",
    department: "",
    program: "",
    batch: "",
    year: "",
    email_pattern: "{given_name}.{family_name}",
    domain: "school.org",
    collision_strategy: "append_numeric",
    priority: 10,
    is_active: true,
  },
];

const DEFAULT_DIRECTORY_AUDIT_LOGS: MockDirectoryAuditLog[] = [
  {
    id: 1,
    actor_email: "admin@school.org",
    action_type: "move_ou",
    target_ref: "alice.brown@school.org",
    is_dry_run: false,
    success: true,
    error_message: "",
    created_at: "2024-03-15T09:30:00Z",
  },
];

const DEFAULT_APPROVAL_REQUESTS: MockApprovalRequest[] = [];

// ─── AdminMockApi class ────────────────────────────────────────────────────────

export class AdminMockApi {
  authenticated: boolean;
  userEmail: string;
  groups: MockGroup[];
  adminCourses: MockAdminCourse[];
  bundles: MockBundle[];
  jobs: MockJob[];
  directoryUsers: MockDirectoryUser[];
  directoryIssues: MockDirectoryIssue[];
  directoryChangeJobs: MockDirectoryChangeJob[];
  provisioningRecords: MockProvisioningRecord[];
  ouTemplates: MockOuTemplate[];
  emailRules: MockEmailRule[];
  directoryAuditLogs: MockDirectoryAuditLog[];
  approvalRequests: MockApprovalRequest[];
  directorySyncJobs: MockDirectorySyncJob[];
  directoryVerifyJobs: MockDirectoryVerifyJob[];
  directoryVerifyRows: MockDirectoryVerifyRow[];
  classroomCoursesError: { status: number; body: Record<string, unknown> } | null;
  private nextBundleId: number;
  private nextJobId: number;
  private nextDirectoryIssueId: number;
  private nextDirectoryJobId: number;
  private nextProvisioningId: number;
  private nextOuTemplateId: number;
  private nextEmailRuleId: number;
  private nextDirectoryAuditId: number;
  private nextApprovalRequestId: number;
  private nextDirectorySyncJobId: number;
  private nextDirectoryVerifyJobId: number;
  private nextDirectoryVerifyRowId: number;

  // Call tracking for assertions
  calls: Record<string, number> = {};

  constructor(options: AdminMockOptions = {}) {
    this.authenticated = options.authenticated ?? true;
    this.userEmail = options.userEmail ?? "admin@school.org";
    this.groups = options.groups ?? DEFAULT_GROUPS.map((g) => ({ ...g }));
    this.adminCourses = options.adminCourses ?? DEFAULT_ADMIN_COURSES.map((c) => ({ ...c }));
    this.bundles = options.bundles ?? DEFAULT_BUNDLES.map((b) => ({ ...b }));
    this.jobs = options.jobs ?? DEFAULT_JOBS.map((j) => ({ ...j }));
    this.directoryUsers = options.directoryUsers ?? DEFAULT_DIRECTORY_USERS.map((u) => ({ ...u }));
    this.directoryIssues = options.directoryIssues ?? DEFAULT_DIRECTORY_ISSUES.map((i) => ({ ...i }));
    this.directoryChangeJobs = options.directoryChangeJobs ?? DEFAULT_DIRECTORY_CHANGE_JOBS.map((j) => ({ ...j }));
    this.provisioningRecords = options.provisioningRecords ?? DEFAULT_PROVISIONING_RECORDS.map((r) => ({ ...r }));
    this.ouTemplates = options.ouTemplates ?? DEFAULT_OU_TEMPLATES.map((r) => ({ ...r }));
    this.emailRules = options.emailRules ?? DEFAULT_EMAIL_RULES.map((r) => ({ ...r }));
    this.directoryAuditLogs = options.directoryAuditLogs ?? DEFAULT_DIRECTORY_AUDIT_LOGS.map((r) => ({ ...r }));
    this.approvalRequests = options.approvalRequests ?? DEFAULT_APPROVAL_REQUESTS.map((r) => ({ ...r }));
    this.directorySyncJobs = options.directorySyncJobs ?? [];
    this.directoryVerifyJobs = options.directoryVerifyJobs ?? [];
    this.directoryVerifyRows = options.directoryVerifyRows ?? [];
    this.classroomCoursesError = options.classroomCoursesError ?? null;
    this.nextBundleId = Math.max(0, ...this.bundles.map((b) => b.id)) + 1;
    this.nextJobId = Math.max(0, ...this.jobs.map((j) => j.id)) + 1;
    this.nextDirectoryIssueId = Math.max(0, ...this.directoryIssues.map((i) => i.id)) + 1;
    this.nextDirectoryJobId = Math.max(0, ...this.directoryChangeJobs.map((j) => j.id)) + 1;
    this.nextProvisioningId = Math.max(0, ...this.provisioningRecords.map((r) => r.id)) + 1;
    this.nextOuTemplateId = Math.max(0, ...this.ouTemplates.map((r) => r.id)) + 1;
    this.nextEmailRuleId = Math.max(0, ...this.emailRules.map((r) => r.id)) + 1;
    this.nextDirectoryAuditId = Math.max(0, ...this.directoryAuditLogs.map((r) => r.id)) + 1;
    this.nextApprovalRequestId = Math.max(0, ...this.approvalRequests.map((r) => r.id)) + 1;
    this.nextDirectorySyncJobId = Math.max(0, ...this.directorySyncJobs.map((r) => r.id)) + 1;
    this.nextDirectoryVerifyJobId = Math.max(0, ...this.directoryVerifyJobs.map((r) => r.id)) + 1;
    this.nextDirectoryVerifyRowId = Math.max(0, ...this.directoryVerifyRows.map((r) => r.id)) + 1;
  }

  private track(name: string) {
    this.calls[name] = (this.calls[name] ?? 0) + 1;
  }

  async attach(page: Page) {
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const pathname = url.pathname;
      const method = route.request().method();

      this.track(`${method} ${pathname}`);

      // ─── Auth ──────────────────────────────────────────────────────────────
      if (pathname === "/api/auth/status") {
        return json(route, this.authenticated
          ? { authenticated: true, user: { name: "Admin User", email: this.userEmail } }
          : { authenticated: false });
      }

      if (pathname === "/api/auth/google/start") {
        return json(route, { auth_url: `${url.origin}/oauth/mock` });
      }

      if (pathname === "/api/auth/logout" && method === "POST") {
        this.authenticated = false;
        return json(route, { ok: true });
      }

      // ─── Core (classrooms/sessions/logs — needed for home page) ───────────
      if (pathname === "/api/classrooms/") return json(route, []);
      if (pathname === "/api/sessions/") return json(route, []);
      if (pathname === "/api/logs/") return json(route, []);

      // ─── Groups ───────────────────────────────────────────────────────────
      if (pathname === "/api/groups" && method === "GET") {
        return json(route, this.groups);
      }

      if (pathname === "/api/groups/sync" && method === "POST") {
        this.track("sync-groups");
        return json(route, { synced: this.groups.length, created: 0, updated: this.groups.length });
      }

      if (pathname === "/api/groups/add-member" && method === "POST") {
        const body = route.request().postDataJSON() as { group_email: string; user_email: string };
        this.track("add-member");
        return json(route, { status: "added", group_email: body.group_email, user_email: body.user_email });
      }

      if (pathname === "/api/groups/remove-member" && method === "POST") {
        const body = route.request().postDataJSON() as { group_email: string; user_email: string };
        this.track("remove-member");
        return json(route, { status: "removed", group_email: body.group_email, user_email: body.user_email });
      }

      const groupMembersMatch = pathname.match(/^\/api\/groups\/([^/]+)\/members$/);
      if (groupMembersMatch && method === "GET") {
        return json(route, { members: [
          { email: "student1@school.org", role: "MEMBER", type: "USER" },
          { email: "student2@school.org", role: "MEMBER", type: "USER" },
        ]});
      }

      // ─── Classroom Admin ──────────────────────────────────────────────────
      if (pathname === "/api/classroom/courses" && method === "GET") {
        if (this.classroomCoursesError) {
          return json(route, this.classroomCoursesError.body, this.classroomCoursesError.status);
        }
        // Backend returns { courses: [...] } — page uses d.courses
        return json(route, { courses: this.adminCourses });
      }
      const rosterMatch = pathname.match(/^\/api\/classroom\/courses\/([^/]+)\/roster$/);
      if (rosterMatch && method === "GET") {
        const courseId = rosterMatch[1];
        return json(route, {
          course_id: courseId,
          students: ["student1@school.org", "student2@school.org"],
          teachers: ["teacher1@school.org"],
          student_count: 2,
          teacher_count: 1,
          total_count: 3,
        });
      }

      if (pathname === "/api/classroom/add-student" && method === "POST") {
        this.track("add-student");
        return json(route, { status: "enrolled" });
      }

      if (pathname === "/api/classroom/add-teacher" && method === "POST") {
        this.track("add-teacher");
        return json(route, { status: "enrolled" });
      }

      if (pathname === "/api/classroom/preflight" && method === "POST") {
        return json(route, { allowed: true, warnings: [], errors: [], metadata: {} });
      }

      if (pathname === "/api/classroom/courses/create" && method === "POST") {
        const body = route.request().postDataJSON() as { name: string; section?: string };
        const newCourse: MockAdminCourse = {
          id: `c-${Date.now()}`, name: body.name, section: body.section ?? "",
          courseState: "ACTIVE", alternateLink: "https://classroom.google.com", ownerId: this.userEmail,
        };
        this.adminCourses.push(newCourse);
        this.track("create-course");
        return json(route, newCourse, 201);
      }

      const archiveMatch = pathname.match(/^\/api\/classroom\/courses\/([^/]+)\/archive$/);
      if (archiveMatch && method === "POST") {
        const courseId = archiveMatch[1];
        const course = this.adminCourses.find((c) => c.id === courseId);
        if (course) course.courseState = "ARCHIVED";
        this.track("archive-course");
        return json(route, { status: "archived", course_id: courseId });
      }

      const courseIdMatch = pathname.match(/^\/api\/classroom\/courses\/([^/]+)$/);
      if (courseIdMatch && method === "DELETE") {
        const courseId = courseIdMatch[1];
        this.adminCourses = this.adminCourses.filter((c) => c.id !== courseId);
        this.track("delete-course");
        return route.fulfill({ status: 204, body: "" });
      }

      if (pathname === "/api/classroom/remove-student" && method === "POST") {
        this.track("remove-student");
        return json(route, { status: "removed" });
      }

      if (pathname === "/api/classroom/remove-teacher" && method === "POST") {
        this.track("remove-teacher");
        return json(route, { status: "removed" });
      }

      // ─── Bundles ──────────────────────────────────────────────────────────
      if (pathname === "/api/bundles" && method === "GET") {
        return json(route, this.bundles);
      }

      if (pathname === "/api/bundles/create" && method === "POST") {
        const body = route.request().postDataJSON() as Partial<MockBundle>;
        const newBundle: MockBundle = {
          id: this.nextBundleId++,
          name: body.name ?? "New Bundle",
          role_type: body.role_type ?? "student",
          groups_json: body.groups_json ?? [],
          classroom_courses_json: body.classroom_courses_json ?? [],
          description: body.description ?? "",
          active: true,
          created_by: this.userEmail,
        };
        this.bundles.push(newBundle);
        this.track("create-bundle");
        return json(route, newBundle, 201);
      }

      const bundleUpdateMatch = pathname.match(/^\/api\/bundles\/(\d+)$/);
      if (bundleUpdateMatch && method === "PATCH") {
        const id = Number(bundleUpdateMatch[1]);
        const bundle = this.bundles.find((b) => b.id === id);
        if (bundle) Object.assign(bundle, route.request().postDataJSON());
        this.track("update-bundle");
        return json(route, bundle ?? { detail: "Not found" }, bundle ? 200 : 404);
      }

      const bundleDeleteMatch = pathname.match(/^\/api\/bundles\/(\d+)\/delete$/);
      if (bundleDeleteMatch && method === "DELETE") {
        const id = Number(bundleDeleteMatch[1]);
        this.bundles = this.bundles.filter((b) => b.id !== id);
        this.track("delete-bundle");
        return route.fulfill({ status: 204, body: "" });
      }

      // ─── Commands ─────────────────────────────────────────────────────────
      if (pathname === "/api/commands/preview" && method === "POST") {
        const body = route.request().postDataJSON() as { command_type?: string; params?: Record<string, string> };
        const commandType = body.command_type || "ADD_STUDENT_TO_COURSE";
        return json(route, {
          action: commandType,
          params: body.params || {},
          items: [{ action: commandType, target_ref: "student@school.org", status: "pending" }],
          summary: { total: 1 },
        });
      }

      if (pathname === "/api/commands/run" && method === "POST") {
        const body = route.request().postDataJSON() as { command_type?: string; dry_run?: boolean };
        const job: MockJob = {
          id: this.nextJobId++,
          job_type: body.command_type || "ADD_STUDENT_TO_COURSE",
          created_by_email: this.userEmail,
          status: body.dry_run ? "dry_run" : "completed",
          dry_run: Boolean(body.dry_run),
          item_count: 1,
          target_summary_json: {},
          result_summary_json: { success: 1, failed: 0, skipped: 0 },
          created_at: new Date().toISOString(),
        };
        this.jobs.push(job);
        this.track("commands-run");
        return json(route, job, 201);
      }

      if (pathname === "/api/commands/jobs" && method === "GET") {
        return json(route, this.jobs);
      }

      const jobDetailMatch = pathname.match(/^\/api\/commands\/jobs\/(\d+)$/);
      if (jobDetailMatch && method === "GET") {
        const id = Number(jobDetailMatch[1]);
        const job = this.jobs.find((j) => j.id === id);
        return json(route, job ? { ...job, items: [] } : { detail: "Not found" }, job ? 200 : 404);
      }

      if (pathname === "/api/commands/logs" && method === "GET") {
        return json(route, [
          { id: 1, actor_email: "admin@school.org", action_type: "ADD_STUDENT_TO_COURSE", job: 1, detail: "Enrolled student@school.org", created_at: "2024-03-10T09:00:00Z" },
        ]);
      }

      if (pathname === "/api/commands/retry" && method === "POST") {
        this.track("retry-job");
        return json(route, { queued: true });
      }

      if (pathname === "/api/commands/import/csv/preview" && method === "POST") {
        return json(route, { rows: [{ row_index: 0, email: "new@school.org", status: "valid", errors: [] }], summary: { valid: 1, invalid: 0 } });
      }

      if (pathname === "/api/commands/import/csv/run" && method === "POST") {
        return json(route, { job_id: this.nextJobId++, status: "queued" });
      }

      // ─── Directory module ──────────────────────────────────────────────────
      if (pathname === "/api/directory/users" && method === "GET") {
        let users = [...this.directoryUsers];
        const q = (url.searchParams.get("q") || "").toLowerCase();
        const category = url.searchParams.get("category") || "";
        if (q) {
          users = users.filter((u) =>
            [u.primary_email, u.full_name, u.external_identifier].join(" ").toLowerCase().includes(q),
          );
        }
        if (category) users = users.filter((u) => u.user_category === category);
        return json(route, users);
      }

      const directoryUserMatch = pathname.match(/^\/api\/directory\/users\/(\d+)$/);
      if (directoryUserMatch && method === "GET") {
        const id = Number(directoryUserMatch[1]);
        const row = this.directoryUsers.find((u) => u.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }
      if (directoryUserMatch && method === "PATCH") {
        const id = Number(directoryUserMatch[1]);
        const row = this.directoryUsers.find((u) => u.id === id);
        if (!row) return json(route, { detail: "Not found" }, 404);
        Object.assign(row, route.request().postDataJSON());
        return json(route, row);
      }

      if (pathname === "/api/directory/sync" && method === "POST") {
        const now = new Date().toISOString();
        this.directoryUsers = this.directoryUsers.map((u) => ({ ...u, last_synced_at: now }));
        this.directorySyncJobs.unshift({
          id: this.nextDirectorySyncJobId++,
          status: "completed",
          completed_at: now,
          pages_fetched: 3,
          users_fetched_total: this.directoryUsers.length,
          users_upserted_total: this.directoryUsers.length,
          users_created_total: 0,
          users_updated_total: this.directoryUsers.length,
          error_message: "",
          created_at: now,
        });
        return json(route, {
          synced: this.directoryUsers.length,
          created: 0,
          updated: this.directoryUsers.length,
          pages_fetched: 3,
          total_directory_users: this.directoryUsers.length,
        });
      }

      if (pathname === "/api/directory/stats" && method === "GET") {
        return json(route, {
          total_directory_users: this.directoryUsers.length,
          latest_sync_job: this.directorySyncJobs[0] ?? null,
          running_sync_job: null,
        });
      }

      if (pathname === "/api/directory/sync-jobs" && method === "GET") {
        return json(route, this.directorySyncJobs);
      }

      const syncJobMatch = pathname.match(/^\/api\/directory\/sync-jobs\/(\d+)$/);
      if (syncJobMatch && method === "GET") {
        const id = Number(syncJobMatch[1]);
        const row = this.directorySyncJobs.find((r) => r.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }

      if (pathname === "/api/directory/issues" && method === "GET") {
        let issues = [...this.directoryIssues];
        const status = url.searchParams.get("status") || "";
        const severity = url.searchParams.get("severity") || "";
        const issueType = url.searchParams.get("issue_type") || "";
        const suggestedAction = url.searchParams.get("suggested_action") || "";
        const q = (url.searchParams.get("q") || "").toLowerCase();
        if (status) issues = issues.filter((i) => i.status === status);
        if (severity) issues = issues.filter((i) => i.severity === severity);
        if (issueType) issues = issues.filter((i) => i.issue_type === issueType);
        if (suggestedAction) issues = issues.filter((i) => i.suggested_action === suggestedAction);
        if (q) {
          issues = issues.filter((i) =>
            [
              i.directory_user_email || "",
              i.issue_type,
              i.actual_value,
              i.expected_value,
              i.suggested_action,
            ]
              .join(" ")
              .toLowerCase()
              .includes(q),
          );
        }
        return json(route, issues);
      }

      const issueMatch = pathname.match(/^\/api\/directory\/issues\/(\d+)$/);
      if (issueMatch && method === "GET") {
        const id = Number(issueMatch[1]);
        const issue = this.directoryIssues.find((i) => i.id === id);
        return json(route, issue ?? { detail: "Not found" }, issue ? 200 : 404);
      }

      if (pathname === "/api/directory/issues/scan" && method === "POST") {
        const created = this.directoryIssues.length === 0 ? 1 : 0;
        if (created) {
          const firstUser = this.directoryUsers[0];
          this.directoryIssues.push({
            id: this.nextDirectoryIssueId++,
            directory_user: firstUser?.id ?? null,
            directory_user_email: firstUser?.primary_email ?? null,
            issue_type: "invalid_org_unit",
            severity: "warning",
            status: "detected",
            actual_value: firstUser?.org_unit_path ?? "",
            expected_value: firstUser?.expected_org_unit_path ?? "",
            suggested_action: "move_ou",
            detected_at: new Date().toISOString(),
          });
        }
        return json(route, { users_scanned: this.directoryUsers.length, issues_created: created });
      }

      const issueActionMatch = pathname.match(/^\/api\/directory\/issues\/(\d+)\/(approve|reject|mark-exception)$/);
      if (issueActionMatch && method === "POST") {
        const id = Number(issueActionMatch[1]);
        const action = issueActionMatch[2];
        const issue = this.directoryIssues.find((i) => i.id === id);
        if (!issue) return json(route, { detail: "Not found" }, 404);
        if (action === "approve") issue.status = "approved";
        if (action === "reject") issue.status = "rejected";
        if (action === "mark-exception") issue.status = "exception_marked";
        return json(route, issue);
      }

      if (pathname === "/api/directory/issues/bulk-approve" && method === "POST") {
        const body = route.request().postDataJSON() as { issue_ids?: number[] };
        const issueIds = body.issue_ids || [];
        this.directoryIssues = this.directoryIssues.map((i) =>
          issueIds.includes(i.id) ? { ...i, status: "approved" } : i,
        );
        return json(route, { updated: issueIds.length });
      }

      if (pathname === "/api/org-units/templates" && method === "GET") {
        return json(route, this.ouTemplates);
      }
      if (pathname === "/api/org-units/templates" && method === "POST") {
        const row = { id: this.nextOuTemplateId++, ...(route.request().postDataJSON() as Record<string, unknown>) } as MockOuTemplate;
        this.ouTemplates.push(row);
        return json(route, row, 201);
      }
      const ouTemplateMatch = pathname.match(/^\/api\/org-units\/templates\/(\d+)$/);
      if (ouTemplateMatch && method === "PATCH") {
        const id = Number(ouTemplateMatch[1]);
        const row = this.ouTemplates.find((r) => r.id === id);
        if (!row) return json(route, { detail: "Not found" }, 404);
        Object.assign(row, route.request().postDataJSON());
        return json(route, row);
      }

      if (pathname === "/api/email-templates" && method === "GET") {
        return json(route, this.emailRules);
      }
      if (pathname === "/api/email-templates" && method === "POST") {
        const row = { id: this.nextEmailRuleId++, ...(route.request().postDataJSON() as Record<string, unknown>) } as MockEmailRule;
        this.emailRules.push(row);
        return json(route, row, 201);
      }
      const emailTemplateMatch = pathname.match(/^\/api\/email-templates\/(\d+)$/);
      if (emailTemplateMatch && method === "PATCH") {
        const id = Number(emailTemplateMatch[1]);
        const row = this.emailRules.find((r) => r.id === id);
        if (!row) return json(route, { detail: "Not found" }, 404);
        Object.assign(row, route.request().postDataJSON());
        return json(route, row);
      }

      if (pathname === "/api/directory/change-jobs/preview" && method === "POST") {
        const body = route.request().postDataJSON() as { job_type?: string; scope_type?: string; issue_ids?: number[] };
        const issueIds = body.issue_ids || [];
        const sourceIssues = this.directoryIssues.filter((issue) =>
          issueIds.length === 0 ? true : issueIds.includes(issue.id),
        );
        const items = sourceIssues.map((issue, idx) => ({
          id: idx + 1,
          issue: issue.id,
          action: issue.suggested_action || "move_ou",
          before_value: issue.actual_value || "",
          after_value: issue.expected_value || "",
          status: "preview_ready",
          result_json: {},
        }));
        const job: MockDirectoryChangeJob = {
          id: this.nextDirectoryJobId++,
          job_type: body.job_type || "ou_correction",
          scope_type: body.scope_type || "issue_selection",
          status: "preview_ready",
          is_dry_run: true,
          item_count: items.length || 1,
          preview_summary: { items: items.length || 1 },
          execution_summary: {},
          items: items.length ? items : [{
            id: 1,
            issue: null,
            action: "move_ou",
            before_value: "/Students/Legacy",
            after_value: "/Students/MBBS/2026",
            status: "preview_ready",
            result_json: {},
          }],
          created_at: new Date().toISOString(),
        };
        this.directoryChangeJobs.unshift(job);
        return json(route, job, 201);
      }

      if (pathname === "/api/directory/change-jobs/execute" && method === "POST") {
        const body = route.request().postDataJSON() as { preview_job_id?: number; dry_run?: boolean; approval_request_id?: number };
        const preview = this.directoryChangeJobs.find((j) => j.id === body.preview_job_id);
        if (!preview) return json(route, { detail: "Preview job not found" }, 404);
        if (preview.scope_type === "bulk" && !body.dry_run) {
          if (!body.approval_request_id) return json(route, { detail: "approval_request_id is required for bulk change execution." }, 400);
          const approval = this.approvalRequests.find((a) => a.id === body.approval_request_id);
          if (!approval) return json(route, { detail: "Approval request not found." }, 404);
          if (approval.status !== "approved") return json(route, { detail: `Approval request status is ${approval.status}, expected approved.` }, 400);
          approval.status = "executed";
          approval.execution_status = "executed";
          approval.execution_message = "Linked execution completed.";
          approval.updated_at = new Date().toISOString();
        }
        const job: MockDirectoryChangeJob = {
          id: this.nextDirectoryJobId++,
          job_type: preview.job_type,
          scope_type: preview.scope_type,
          status: "completed",
          is_dry_run: Boolean(body.dry_run),
          item_count: preview.item_count,
          preview_summary: preview.preview_summary,
          execution_summary: { success: preview.item_count, failed: 0 },
          items: (preview.items || []).map((item) => ({
            ...item,
            status: "applied",
            result_json: { success: true },
          })),
          created_at: new Date().toISOString(),
        };
        this.directoryChangeJobs.unshift(job);
        this.directoryAuditLogs.unshift({
          id: this.nextDirectoryAuditId++,
          actor_email: this.userEmail,
          action_type: "move_ou",
          target_ref: "bulk",
          is_dry_run: Boolean(body.dry_run),
          success: true,
          error_message: "",
          created_at: new Date().toISOString(),
        });
        return json(route, job);
      }

      if (pathname === "/api/directory/change-jobs" && method === "GET") {
        return json(route, this.directoryChangeJobs);
      }
      const changeJobMatch = pathname.match(/^\/api\/directory\/change-jobs\/(\d+)$/);
      if (changeJobMatch && method === "GET") {
        const id = Number(changeJobMatch[1]);
        const row = this.directoryChangeJobs.find((j) => j.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }

      if (pathname === "/api/directory/approvals" && method === "GET") {
        let rows = [...this.approvalRequests];
        const status = url.searchParams.get("status");
        const actionType = url.searchParams.get("action_type");
        if (status) rows = rows.filter((r) => r.status === status);
        if (actionType) rows = rows.filter((r) => r.action_type === actionType);
        return json(route, rows);
      }
      if (pathname === "/api/directory/approvals" && method === "POST") {
        const body = route.request().postDataJSON() as Record<string, unknown>;
        const now = new Date().toISOString();
        const row: MockApprovalRequest = {
          id: this.nextApprovalRequestId++,
          action_type: String(body.action_type || "high_risk_mutation"),
          target_type: String(body.target_type || "mutation_scope"),
          target_reference: String(body.target_reference || ""),
          payload: (body.payload as Record<string, unknown>) || {},
          requested_by_email: this.userEmail,
          requested_at: now,
          status: "pending",
          reviewed_by_email: null,
          reviewed_at: null,
          review_notes: "",
          execution_status: "not_started",
          execution_message: "",
          linked_change_job: Number(body.linked_change_job_id || 0) || null,
          linked_provisioning_record: Number(body.linked_provisioning_record_id || 0) || null,
          created_at: now,
          updated_at: now,
        };
        this.approvalRequests.unshift(row);
        return json(route, row, 201);
      }
      const approvalDetailMatch = pathname.match(/^\/api\/directory\/approvals\/(\d+)$/);
      if (approvalDetailMatch && method === "GET") {
        const id = Number(approvalDetailMatch[1]);
        const row = this.approvalRequests.find((r) => r.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }
      const approvalApproveMatch = pathname.match(/^\/api\/directory\/approvals\/(\d+)\/approve$/);
      if (approvalApproveMatch && method === "POST") {
        const id = Number(approvalApproveMatch[1]);
        const row = this.approvalRequests.find((r) => r.id === id);
        if (!row) return json(route, { detail: "Not found" }, 404);
        const body = route.request().postDataJSON() as { review_notes?: string };
        row.status = "approved";
        row.execution_status = "ready_to_execute";
        row.reviewed_by_email = this.userEmail;
        row.reviewed_at = new Date().toISOString();
        row.review_notes = body.review_notes || "";
        row.updated_at = new Date().toISOString();
        return json(route, row);
      }
      const approvalRejectMatch = pathname.match(/^\/api\/directory\/approvals\/(\d+)\/reject$/);
      if (approvalRejectMatch && method === "POST") {
        const id = Number(approvalRejectMatch[1]);
        const row = this.approvalRequests.find((r) => r.id === id);
        if (!row) return json(route, { detail: "Not found" }, 404);
        const body = route.request().postDataJSON() as { review_notes?: string };
        row.status = "rejected";
        row.execution_status = "not_started";
        row.reviewed_by_email = this.userEmail;
        row.reviewed_at = new Date().toISOString();
        row.review_notes = body.review_notes || "";
        row.updated_at = new Date().toISOString();
        return json(route, row);
      }
      const approvalCancelMatch = pathname.match(/^\/api\/directory\/approvals\/(\d+)\/cancel$/);
      if (approvalCancelMatch && method === "POST") {
        const id = Number(approvalCancelMatch[1]);
        const row = this.approvalRequests.find((r) => r.id === id);
        if (!row) return json(route, { detail: "Not found" }, 404);
        const body = route.request().postDataJSON() as { review_notes?: string };
        row.status = "cancelled";
        row.execution_status = "not_started";
        row.reviewed_by_email = this.userEmail;
        row.reviewed_at = new Date().toISOString();
        row.review_notes = body.review_notes || "";
        row.updated_at = new Date().toISOString();
        return json(route, row);
      }

      if (pathname === "/api/provisioning/preview" && method === "POST") {
        const body = route.request().postDataJSON() as Record<string, string>;
        const fullName = (body.full_name || "").trim();
        if (!fullName) return json(route, { detail: "full_name is required" }, 400);
        const emailLocal = fullName.toLowerCase().replace(/[^a-z0-9]+/g, ".").replace(/^\.+|\.+$/g, "");
        const record: MockProvisioningRecord = {
          id: this.nextProvisioningId++,
          full_name: fullName,
          user_category: body.user_category || "student",
          generated_email: `${emailLocal}@school.org`,
          target_org_unit_path: "/Students/MBBS/2026",
          status: "previewed",
          failure_reason: "",
          created_at: new Date().toISOString(),
        };
        this.provisioningRecords.unshift(record);
        return json(route, record, 201);
      }

      if (pathname === "/api/provisioning/create" && method === "POST") {
        const body = route.request().postDataJSON() as { preview_record_id?: number };
        const row = this.provisioningRecords.find((r) => r.id === body.preview_record_id);
        if (!row) return json(route, { detail: "Preview record not found" }, 404);
        row.status = "executed";
        this.directoryAuditLogs.unshift({
          id: this.nextDirectoryAuditId++,
          actor_email: this.userEmail,
          action_type: "create_user",
          target_ref: row.generated_email,
          is_dry_run: false,
          success: true,
          error_message: "",
          created_at: new Date().toISOString(),
        });
        return json(route, row);
      }

      if (pathname === "/api/provisioning/bulk-preview" && method === "POST") {
        const body = route.request().postDataJSON() as { rows?: Array<Record<string, string>> };
        const rows = body.rows || [];
        const records: MockProvisioningRecord[] = [];
        const errors: { row: number; detail: string }[] = [];
        rows.forEach((r, idx) => {
          const fullName = (r.full_name || "").trim();
          if (!fullName) {
            errors.push({ row: idx + 2, detail: "full_name is required" });
            return;
          }
          const emailLocal = fullName.toLowerCase().replace(/[^a-z0-9]+/g, ".").replace(/^\.+|\.+$/g, "");
          const rowRec: MockProvisioningRecord = {
            id: this.nextProvisioningId++,
            full_name: fullName,
            user_category: r.user_category || "student",
            generated_email: `${emailLocal}@school.org`,
            target_org_unit_path: "/Students/MBBS/2026",
            status: "previewed",
            failure_reason: "",
            created_at: new Date().toISOString(),
          };
          this.provisioningRecords.unshift(rowRec);
          records.push(rowRec);
        });
        return json(route, {
          records,
          errors,
          preview_count: records.length,
          error_count: errors.length,
        });
      }

      if (pathname === "/api/provisioning/bulk-create" && method === "POST") {
        const body = route.request().postDataJSON() as { preview_record_ids?: number[]; approval_request_id?: number };
        const ids = body.preview_record_ids || [];
        if (!body.approval_request_id) return json(route, { detail: "approval_request_id is required for bulk provisioning create." }, 400);
        const approval = this.approvalRequests.find((a) => a.id === body.approval_request_id);
        if (!approval) return json(route, { detail: "Approval request not found." }, 404);
        if (approval.status !== "approved") return json(route, { detail: `Approval request status is ${approval.status}, expected approved.` }, 400);
        this.provisioningRecords = this.provisioningRecords.map((r) =>
          ids.includes(r.id) ? { ...r, status: "queued" } : r,
        );
        approval.status = "executed";
        approval.execution_status = "executed";
        approval.execution_message = "Linked provisioning execution queued.";
        approval.updated_at = new Date().toISOString();
        return json(route, { queued: true, record_count: ids.length, task_id: "mock-task-1" });
      }

      if (pathname === "/api/provisioning/records" && method === "GET") {
        return json(route, this.provisioningRecords);
      }
      const provisioningRecordMatch = pathname.match(/^\/api\/provisioning\/records\/(\d+)$/);
      if (provisioningRecordMatch && method === "GET") {
        const id = Number(provisioningRecordMatch[1]);
        const row = this.provisioningRecords.find((r) => r.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }

      if (pathname === "/api/directory/audit-logs" && method === "GET") {
        return json(route, this.directoryAuditLogs);
      }
      const auditLogMatch = pathname.match(/^\/api\/directory\/audit-logs\/(\d+)$/);
      if (auditLogMatch && method === "GET") {
        const id = Number(auditLogMatch[1]);
        const row = this.directoryAuditLogs.find((r) => r.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }

      if (pathname === "/api/directory/verify-upload" && method === "POST") {
        const raw = route.request().postData() || "";
        if (!raw.includes('name="mapping"')) {
          return json(route, {
            requires_mapping: true,
            source_filename: "upload.csv",
            source_type: "csv",
            sheet_name: "",
            available_sheets: [],
            headers: ["Name", "Roll No", "Email Address", "Phone Number", "Official Email Issued", "Email PMC"],
            suggested_mapping: {
              name: "Name",
              roll_no: "Roll No",
              email_address: "Email Address",
              phone_number: "Phone Number",
              official_email_issued: "Official Email Issued",
              email_pmc: "Email PMC",
            },
            row_count: 2,
            sample_rows: [
              { Name: "Alice Brown", "Roll No": "1001", "Official Email Issued": "alice.brown@school.org" },
              { Name: "Unknown User", "Roll No": "9999", "Email Address": "unknown@example.com" },
            ],
          });
        }

        const now = new Date().toISOString();
        const job: MockDirectoryVerifyJob = {
          id: this.nextDirectoryVerifyJobId++,
          source_filename: "upload.csv",
          source_type: "csv",
          sheet_name: "",
          status: "completed",
          row_count: 2,
          summary_json: { total_rows: 2, exists: 1, does_not_exist: 1, ambiguous: 0, invalid_input: 0 },
          column_mapping_json: {},
          created_at: now,
          completed_at: now,
        };
        this.directoryVerifyJobs.unshift(job);
        this.directoryVerifyRows = this.directoryVerifyRows.filter((r) => r.job !== job.id);
        this.directoryVerifyRows.push(
          {
            id: this.nextDirectoryVerifyRowId++,
            job: job.id,
            row_no: 2,
            input_json: { name: "Alice Brown", roll_no: "1001", official_email_issued: "alice.brown@school.org", email_address: "", phone_number: "", email_pmc: "" },
            matched_email: "alice.brown@school.org",
            matched_name: "Alice Brown",
            match_basis: "exact_official_email",
            verdict: "exists",
            notes: "Matched by exact primary email.",
          },
          {
            id: this.nextDirectoryVerifyRowId++,
            job: job.id,
            row_no: 3,
            input_json: { name: "Unknown User", roll_no: "9999", official_email_issued: "", email_address: "unknown@example.com", phone_number: "", email_pmc: "" },
            matched_email: "",
            matched_name: "",
            match_basis: "no_match",
            verdict: "does_not_exist",
            notes: "No matching directory user found.",
          },
        );
        return json(route, job, 201);
      }

      if (pathname === "/api/directory/verify-jobs" && method === "GET") {
        return json(route, this.directoryVerifyJobs);
      }

      const verifyJobMatch = pathname.match(/^\/api\/directory\/verify-jobs\/(\d+)$/);
      if (verifyJobMatch && method === "GET") {
        const id = Number(verifyJobMatch[1]);
        const row = this.directoryVerifyJobs.find((r) => r.id === id);
        return json(route, row ?? { detail: "Not found" }, row ? 200 : 404);
      }

      const verifyRowsMatch = pathname.match(/^\/api\/directory\/verify-jobs\/(\d+)\/rows$/);
      if (verifyRowsMatch && method === "GET") {
        const id = Number(verifyRowsMatch[1]);
        const verdict = url.searchParams.get("verdict") || "";
        const page = Number(url.searchParams.get("page") || "1");
        const pageSize = Number(url.searchParams.get("page_size") || "25");
        let rows = this.directoryVerifyRows.filter((r) => r.job === id);
        if (verdict) rows = rows.filter((r) => r.verdict === verdict);
        const start = (page - 1) * pageSize;
        const sliced = rows.slice(start, start + pageSize);
        return json(route, { total: rows.length, page, page_size: pageSize, results: sliced });
      }

      const verifyExportMatch = pathname.match(/^\/api\/directory\/verify-jobs\/(\d+)\/export$/);
      if (verifyExportMatch && method === "GET") {
        return route.fulfill({
          status: 200,
          contentType: "text/csv",
          body: "row_no,name,verdict\n2,Alice Brown,exists\n3,Unknown User,does_not_exist\n",
        });
      }

      // Fallback
      return json(route, { detail: `Unhandled: ${method} ${pathname}` }, 500);
    });

    await page.route("**/oauth/mock", async (route) => {
      await route.fulfill({ status: 200, contentType: "text/html", body: "<html><body><h1>Mock OAuth</h1></body></html>" });
    });
  }
}
