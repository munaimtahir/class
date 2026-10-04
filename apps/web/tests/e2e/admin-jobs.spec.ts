/**
 * Admin Jobs & Logs page tests
 * Covers: list jobs, view job detail, retry failed jobs, audit logs tab.
 */
import { test, expect } from "@playwright/test";
import { AdminMockApi } from "./mock-admin-api";

test.describe("Jobs page — jobs tab", () => {
  test("lists command jobs in a table", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await expect(page.locator("h1")).toContainText(/Jobs/i);
    await expect(page.locator("text=Add Student").first()).toBeVisible();
  });

  test("shows job status badges", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await expect(page.locator("text=completed").first()).toBeVisible();
  });

  test("shows 'partial' status badge for partial jobs", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await expect(page.locator("text=partial").first()).toBeVisible();
  });

  test("empty state shown when no jobs exist", async ({ page }) => {
    const mock = new AdminMockApi({ jobs: [] });
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await expect(page.locator("text=/No jobs yet/i")).toBeVisible();
  });

  test("clicking Details loads job detail panel via GET /api/commands/jobs/{id}", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await page.locator("button", { hasText: "Details" }).first().click();
    // Job detail panel should appear
    await expect(page.locator("text=/#1|Job #/i").first()).toBeVisible();
    expect(mock.calls["GET /api/commands/jobs/1"]).toBe(1);
  });

  test("retry button is shown for jobs with failed items", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    // Job #2 has 1 failed item — should show Retry button
    const retryBtn = page.locator("button", { hasText: "Retry" });
    await expect(retryBtn).toBeVisible();
  });

  test("clicking Retry calls POST /api/commands/retry", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    const retryBtn = page.locator("button", { hasText: "Retry" }).first();
    await expect(retryBtn).toBeVisible();
    await retryBtn.click();
    expect(mock.calls["POST /api/commands/retry"]).toBe(1);
  });

  test("shows Phase 2B action types with human-readable labels", async ({ page }) => {
    const mock = new AdminMockApi({
      jobs: [
        { id: 10, job_type: "CREATE_COURSE", created_by_email: "admin@school.org", status: "completed", dry_run: false, item_count: 1, target_summary_json: {}, result_summary_json: { success: 1, failed: 0, skipped: 0 }, created_at: new Date().toISOString() },
        { id: 11, job_type: "ARCHIVE_COURSE", created_by_email: "admin@school.org", status: "completed", dry_run: false, item_count: 1, target_summary_json: {}, result_summary_json: { success: 1, failed: 0, skipped: 0 }, created_at: new Date().toISOString() },
        { id: 12, job_type: "REMOVE_STUDENT_FROM_COURSE", created_by_email: "admin@school.org", status: "completed", dry_run: false, item_count: 1, target_summary_json: {}, result_summary_json: { success: 1, failed: 0, skipped: 0 }, created_at: new Date().toISOString() },
      ],
    });
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await expect(page.locator("text=Create Course")).toBeVisible();
    await expect(page.locator("text=Archive Course")).toBeVisible();
    await expect(page.locator("text=Remove Student")).toBeVisible();
  });
});

test.describe("Jobs page — audit logs tab", () => {
  test("Audit Logs tab is visible", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await expect(page.locator("button, [role=tab]", { hasText: /Audit Logs/i })).toBeVisible();
  });

  test("clicking Audit Logs tab loads logs via GET /api/commands/logs", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await page.locator("button", { hasText: /Audit Logs/i }).click();
    await expect(page.locator("text=admin@school.org").first()).toBeVisible();
    expect(mock.calls["GET /api/commands/logs"]).toBe(1);
  });

  test("audit log shows action type with human-readable label", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    await page.locator("button", { hasText: /Audit Logs/i }).click();
    await expect(page.locator("text=Add Student")).toBeVisible();
  });
});

test.describe("Jobs page — refresh", () => {
  test("Refresh button re-fetches job list", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/jobs");
    const initialCallCount = mock.calls["GET /api/commands/jobs"] ?? 0;
    await page.locator("button", { hasText: /Refresh/i }).click();
    await page.waitForTimeout(300);
    expect((mock.calls["GET /api/commands/jobs"] ?? 0)).toBeGreaterThan(initialCallCount);
  });
});
