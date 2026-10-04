import { api } from "./api";

type ActivityItem = {
  title: string;
  detail: string;
  tone: "default" | "warning" | "danger";
};

type AlertItem = {
  title: string;
  detail: string;
  severity: "info" | "warning" | "critical";
};

export type WorkspaceDashboardData = {
  connectionStatus: "connected" | "disconnected";
  lastWorkspaceSync: string | null;
  lastClassroomSync: string | null;
  directorySyncStatus: "running" | "completed" | "never";
  totalSyncedUsers: number;
  totalActiveCourses: number;
  pendingPublishJobs: number;
  failedPublishJobs: number;
  unresolvedIssues: number;
  recentActivity: ActivityItem[];
  alerts: AlertItem[];
};

function formatStatusLabel(status: unknown): string {
  if (typeof status !== "string" || status.length === 0) {
    return "updated";
  }
  return status.toLowerCase().replaceAll("_", " ");
}

function fallbackData(): WorkspaceDashboardData {
  return {
    connectionStatus: "disconnected",
    lastWorkspaceSync: null,
    lastClassroomSync: null,
    directorySyncStatus: "never",
    totalSyncedUsers: 0,
    totalActiveCourses: 0,
    pendingPublishJobs: 0,
    failedPublishJobs: 0,
    unresolvedIssues: 0,
    recentActivity: [
      {
        title: "No recent activity",
        detail: "Activity will appear here after sync or publishing actions.",
        tone: "default",
      },
    ],
    alerts: [
      {
        title: "Data adapter fallback",
        detail: "Live metrics are temporarily unavailable; showing safe defaults.",
        severity: "info",
      },
    ],
  };
}

export async function loadWorkspaceDashboardData(): Promise<WorkspaceDashboardData> {
  const fallback = fallbackData();

  const [authStatus, directoryStats, courses, sessions, issues, logs] = await Promise.all([
    api.authStatus().catch(() => null),
    api.directoryStats().catch(() => null),
    api.courses().catch(() => []),
    api.sessions().catch(() => []),
    api.listDirectoryIssues({}).catch(() => []),
    api.logs().catch(() => []),
  ]);

  const sessionList = Array.isArray(sessions) ? sessions : [];
  const issueList = Array.isArray(issues) ? issues : [];
  const logList = Array.isArray(logs) ? logs : [];

  const pendingPublishJobs = sessionList.filter(
    (session: { status?: string }) => session.status === "scheduled",
  ).length;
  const failedPublishJobs = sessionList.filter(
    (session: { status?: string }) => session.status === "failed",
  ).length;
  const unresolvedIssues = issueList.filter((issue: { status?: string }) => {
    const status = typeof issue.status === "string" ? issue.status.toLowerCase() : "";
    return !["applied", "resolved", "closed", "rejected"].includes(status);
  }).length;

  const recentActivity = logList
    .slice(0, 5)
    .map((log: { status?: string; message?: string; created_at?: string }) => {
      const tone: ActivityItem["tone"] =
        log.status === "failed" ? "danger" : log.status === "scheduled" ? "warning" : "default";
      return {
        title: formatStatusLabel(log.status),
        detail: `${log.message || "Update"}${
          log.created_at ? ` • ${new Date(log.created_at).toLocaleString()}` : ""
        }`,
        tone,
      };
    });

  const alerts: AlertItem[] = [];
  if (failedPublishJobs > 0) {
    alerts.push({
      title: "Failed publish jobs detected",
      detail: `${failedPublishJobs} publish job(s) need retry or review.`,
      severity: "critical",
    });
  }
  if (unresolvedIssues > 0) {
    alerts.push({
      title: "Unresolved operational issues",
      detail: `${unresolvedIssues} issue(s) are still open for resolution.`,
      severity: "warning",
    });
  }
  if (directoryStats?.running_sync_job) {
    alerts.push({
      title: "Directory sync in progress",
      detail: `Fetched ${directoryStats.running_sync_job.users_fetched_total} users so far.`,
      severity: "info",
    });
  }
  if (alerts.length === 0) {
    alerts.push({
      title: "No active warnings",
      detail: "Core workspace operations appear stable.",
      severity: "info",
    });
  }

  return {
    connectionStatus: authStatus?.authenticated ? "connected" : fallback.connectionStatus,
    lastWorkspaceSync: directoryStats?.latest_sync_job?.completed_at || null,
    lastClassroomSync: logList[0]?.created_at || null,
    directorySyncStatus: directoryStats?.running_sync_job
      ? "running"
      : directoryStats?.latest_sync_job
        ? "completed"
        : "never",
    totalSyncedUsers: directoryStats?.total_directory_users ?? fallback.totalSyncedUsers,
    totalActiveCourses: Array.isArray(courses) ? courses.length : fallback.totalActiveCourses,
    pendingPublishJobs,
    failedPublishJobs,
    unresolvedIssues,
    recentActivity: recentActivity.length > 0 ? recentActivity : fallback.recentActivity,
    alerts,
  };
}
