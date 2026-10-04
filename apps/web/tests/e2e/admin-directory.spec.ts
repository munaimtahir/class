import { expect, test } from "@playwright/test";

import { AdminMockApi } from "./mock-admin-api";

test.describe("Directory module pages", () => {
  test("dashboard shows summary and can trigger sync + scan", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/directory");
    await expect(page.locator("h1")).toContainText("Directory Dashboard");
    await expect(page.locator("text=Synced users")).toBeVisible();

    await page.getByRole("button", { name: "Sync Directory" }).click();
    await expect(page.locator("text=/Directory sync complete/i")).toBeVisible();

    await page.getByRole("button", { name: "Scan Issues" }).click();
    await expect(page.locator("text=/Issue scan complete/i")).toBeVisible();

    expect(mock.calls["POST /api/directory/sync"]).toBe(1);
    expect(mock.calls["POST /api/directory/issues/scan"]).toBe(1);
  });

  test("users page supports filtering and detail inspection", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/directory/users");
    await expect(page.locator("h1")).toContainText("Directory Users");
    await expect(page.locator("td", { hasText: "alice.brown@school.org" })).toBeVisible();

    await page.locator("input[placeholder='Search email, name, identifier']").fill("alice");
    await page.getByRole("button", { name: "Apply" }).click();
    await page.locator("tbody tr", { hasText: "alice.brown@school.org" }).click();

    await expect(page.locator("text=User Details")).toBeVisible();
    await expect(page.locator("text=Issue badges")).toBeVisible();
  });

  test("issues page can approve, preview, and execute selected issues", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/directory/issues");
    await expect(page.locator("h1")).toContainText("Inconsistency Review");
    await expect(page.locator("th", { hasText: "Fix Plan (Before Preview)" })).toBeVisible();
    await page.locator("select").nth(2).selectOption("invalid_org_unit");
    await page.locator("input[placeholder='Search user/type/action/value']").fill("alice");
    await page.getByRole("button", { name: "Apply Filters" }).click();
    await expect(page.locator("td", { hasText: "alice.brown@school.org" })).toBeVisible();

    await page.getByLabel("Select issue 1").check();
    await page.getByRole("button", { name: /Bulk Approve/i }).click();
    await expect(page.locator("td", { hasText: "approved" })).toBeVisible();

    await page.getByLabel("Select issue 1").check();
    await page.getByRole("button", { name: "Preview Suggested Fixes" }).click();
    await expect(page.getByText(/Preview job #\d+ ready/i)).toBeVisible();
    await expect(page.locator("text=Preview:")).toBeVisible();

    await page.getByRole("button", { name: "Execute Approved Preview" }).click();
    await expect.poll(() => mock.calls["POST /api/directory/change-jobs/execute"] ?? 0).toBe(1);
    await expect(page.locator("text=Executed:")).toBeVisible();

    expect(mock.calls["POST /api/directory/change-jobs/preview"]).toBe(1);
  });

  test("rules page can create OU and email template entries", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/directory/rules");
    await expect(page.locator("h1")).toContainText("OU Templates & Email Rules");

    const ouSection = page.locator("section").nth(0);
    await ouSection.locator("input[required]").first().fill("Faculty OU Rule");
    await ouSection.locator("input[required]").nth(1).fill("/Faculty/Medicine");
    await ouSection.getByRole("button", { name: "Create OU Template" }).click();
    await expect(page.locator("text=OU template saved.")).toBeVisible();

    const emailSection = page.locator("section").nth(1);
    await emailSection.locator("input[required]").first().fill("Faculty Email Rule");
    await emailSection.locator("input[required]").nth(1).fill("school.org");
    await emailSection.getByRole("button", { name: "Create Email Rule" }).click();
    await expect(page.locator("text=Email template rule saved.")).toBeVisible();

    expect(mock.calls["POST /api/org-units/templates"]).toBe(1);
    expect(mock.calls["POST /api/email-templates"]).toBe(1);
  });

  test("provisioning and operations pages show preview/create and audit logs", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/directory/provisioning");
    await expect(page.locator("h1")).toContainText("Create New IDs");

    await page.locator("input").first().fill("Bob Stone");
    await page.getByRole("button", { name: "Preview" }).click();
    await expect(page.locator("text=Generated email:")).toBeVisible();

    await page.getByRole("button", { name: "Create", exact: true }).click();
    await expect(page.locator("text=/Provisioning result:/i")).toBeVisible();

    await page.goto("/admin/directory/jobs");
    await expect(page.locator("h1")).toContainText("Operations Log");
    await expect(page.locator("text=ou_correction")).toBeVisible();
    await page.getByRole("button", { name: "Audit Logs" }).click();
    await expect(page.locator("text=move_ou")).toBeVisible();
  });

  test("approval request review flow works for restricted actions", async ({ page }) => {
    const mock = new AdminMockApi({
      directoryChangeJobs: [
        {
          id: 44,
          job_type: "ou_correction",
          scope_type: "bulk",
          status: "preview_ready",
          is_dry_run: true,
          item_count: 2,
          preview_summary: { items: 2 },
          execution_summary: {},
          created_at: new Date().toISOString(),
        },
      ],
    });
    await mock.attach(page);

    await page.goto("/admin/directory/jobs");
    await page.getByRole("button", { name: "Request Approval" }).click();
    await expect(page.locator("text=/Approval request #/i")).toBeVisible();

    await page.goto("/admin/directory/approvals");
    await expect(page.locator("h1")).toContainText("Approval Requests");
    await expect(page.locator("td", { hasText: "pending" })).toBeVisible();
    await page.getByRole("button", { name: "Approve" }).click();
    await page.getByRole("button", { name: /History/i }).click();
    await expect(page.locator("td", { hasText: "approved" })).toBeVisible();
  });

  test("verification page supports upload, mapping, verdict table, and export actions", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/directory/verification");
    await expect(page.locator("h1")).toContainText("Directory Verification");
    await expect(page.locator("text=Total synced users")).toBeVisible();

    await page.getByRole("button", { name: "Sync Directory" }).click();
    await expect(page.locator("text=/Directory sync complete/i")).toBeVisible();

    await page.setInputFiles("input[type='file']", {
      name: "verify.csv",
      mimeType: "text/csv",
      buffer: Buffer.from(
        "Name,Roll No,Email Address,Phone Number,Official Email Issued,Email PMC\nAlice Brown,1001,,,alice.brown@school.org,\nUnknown User,9999,unknown@example.com,,,\n",
      ),
    });

    await page.getByRole("button", { name: "Analyze Headers" }).click();
    await expect(page.locator("text=/Rows detected/i")).toBeVisible();

    await page.getByRole("button", { name: "Run Verification" }).click();
    await expect(page.locator("text=/Verification completed/i")).toBeVisible();

    await expect(page.locator("text=Total rows")).toBeVisible();
    await expect(page.locator("td", { hasText: "exists" })).toBeVisible();
    await expect(page.locator("td", { hasText: "does_not_exist" })).toBeVisible();

    await expect(page.getByRole("button", { name: "Export CSV" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Export XLSX" })).toBeVisible();
  });
});
