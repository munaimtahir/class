import { api } from "./api";

export type BadgeKey =
  | "failedPublishJobs"
  | "unresolvedIssues"
  | "missingEmails"
  | "ouIssues";

export type NavItem = {
  href: string;
  label: string;
  exact?: boolean;
  matchPaths?: string[];
  badgeKey?: BadgeKey;
};

export type NavModule = {
  id: string;
  label: string;
  items: NavItem[];
};

export type NavBadgeCounts = Record<BadgeKey, number>;

export const DEFAULT_BADGE_COUNTS: NavBadgeCounts = {
  failedPublishJobs: 0,
  unresolvedIssues: 0,
  missingEmails: 0,
  ouIssues: 0,
};

export const NAV_MODULES: NavModule[] = [
  {
    id: "workspace",
    label: "Workspace Dashboard",
    items: [{ href: "/", label: "Workspace Dashboard", exact: true }],
  },
  {
    id: "classroom",
    label: "Classroom Operations",
    items: [
      { href: "/classroom/dashboard", label: "Classroom Dashboard" },
      {
        href: "/classroom/courses",
        label: "Courses",
        matchPaths: ["/admin/courses"],
      },
      {
        href: "/classroom/import-sessions",
        label: "Import Sessions",
        matchPaths: ["/imports"],
      },
      { href: "/classroom/session-drafts", label: "Session Drafts" },
      { href: "/classroom/review-sessions", label: "Review Sessions" },
      {
        href: "/classroom/publish-planner",
        label: "Publish Planner",
        matchPaths: ["/publish"],
      },
      {
        href: "/classroom/publish-jobs",
        label: "Publish Jobs",
        badgeKey: "failedPublishJobs",
      },
      { href: "/classroom/posting-logs", label: "Posting Logs" },
    ],
  },
  {
    id: "resolution",
    label: "User Resolution Center",
    items: [
      { href: "/resolution/dashboard", label: "Issues Dashboard" },
      { href: "/resolution/issues", label: "All Issues" },
      { href: "/resolution/new", label: "New Issue" },
      {
        href: "/resolution/unresolved",
        label: "Unresolved",
        badgeKey: "unresolvedIssues",
      },
      { href: "/resolution/assigned", label: "Assigned to Me" },
      { href: "/resolution/escalated", label: "Escalated" },
    ],
  },
  {
    id: "directory",
    label: "Directory Management",
    items: [
      {
        href: "/directory/dashboard",
        label: "Directory Dashboard",
        matchPaths: ["/admin/directory"],
      },
      {
        href: "/directory/user-search",
        label: "User Search",
        matchPaths: ["/admin/directory/users"],
      },
      {
        href: "/directory/bulk-search",
        label: "Bulk Search",
        matchPaths: ["/admin/directory/verification"],
      },
      {
        href: "/directory/missing-emails",
        label: "Missing Emails",
        badgeKey: "missingEmails",
      },
      {
        href: "/directory/ou-issues",
        label: "Organizational Unit Issues",
        badgeKey: "ouIssues",
      },
      {
        href: "/directory/conflict-review",
        label: "Conflict Review",
        matchPaths: ["/admin/directory/issues"],
      },
      { href: "/directory/sync-history", label: "Sync History" },
    ],
  },
  {
    id: "enrollment",
    label: "Enrollment Management",
    items: [
      { href: "/enrollment/dashboard", label: "Enrollment Dashboard" },
      {
        href: "/enrollment/course-membership-check",
        label: "Course Membership Check",
      },
      { href: "/enrollment/missing-enrollments", label: "Missing Enrollments" },
      { href: "/enrollment/wrong-enrollments", label: "Wrong Enrollments" },
      { href: "/enrollment/group-mapping", label: "Group Mapping" },
      { href: "/enrollment/sync-tools", label: "Enrollment Sync Tools" },
    ],
  },
  {
    id: "administration",
    label: "Administration",
    items: [
      { href: "/administration/workspace-connection", label: "Workspace Connection" },
      { href: "/administration/sync-controls", label: "Sync Controls" },
      {
        href: "/administration/audit-logs",
        label: "Audit Logs",
        matchPaths: ["/admin/directory/jobs", "/admin/jobs"],
      },
      { href: "/administration/settings", label: "Settings" },
      { href: "/admin/groups", label: "Groups (Legacy)" },
      { href: "/admin/bundles", label: "Bundles (Legacy)" },
      { href: "/admin/commands", label: "Commands (Legacy)" },
      { href: "/admin/jobs", label: "Jobs (Legacy)" },
    ],
  },
];

export function isItemActive(pathname: string, item: NavItem): boolean {
  if (item.exact && pathname === item.href) {
    return true;
  }
  if (!item.exact && pathname.startsWith(item.href)) {
    return true;
  }
  return (item.matchPaths || []).some((path) => pathname.startsWith(path));
}

export function getNavContext(pathname: string): { module: string; page: string } | null {
  for (const module of NAV_MODULES) {
    for (const item of module.items) {
      if (isItemActive(pathname, item)) {
        return { module: module.label, page: item.label };
      }
    }
  }
  return null;
}

function isUnresolvedIssue(status: unknown): boolean {
  if (typeof status !== "string") {
    return false;
  }
  return !["applied", "resolved", "closed", "rejected"].includes(status.toLowerCase());
}

function issueTypeIncludes(issueType: unknown, token: string): boolean {
  if (typeof issueType !== "string") {
    return false;
  }
  return issueType.toLowerCase().includes(token);
}

export async function loadNavBadges(): Promise<NavBadgeCounts> {
  const badges = { ...DEFAULT_BADGE_COUNTS };
  try {
    const [sessions, issues] = await Promise.all([
      api.sessions().catch(() => []),
      api.listDirectoryIssues({}).catch(() => []),
    ]);

    if (Array.isArray(sessions)) {
      badges.failedPublishJobs = sessions.filter(
        (session: { status?: string }) => session.status === "failed",
      ).length;
    }

    if (Array.isArray(issues)) {
      badges.unresolvedIssues = issues.filter((issue: { status?: string }) =>
        isUnresolvedIssue(issue.status),
      ).length;
      badges.missingEmails = issues.filter((issue: { issue_type?: string }) =>
        issueTypeIncludes(issue.issue_type, "email"),
      ).length;
      badges.ouIssues = issues.filter((issue: { issue_type?: string }) =>
        issueTypeIncludes(issue.issue_type, "org") ||
        issueTypeIncludes(issue.issue_type, "ou")
      ).length;
    }
  } catch {
    return badges;
  }
  return badges;
}
