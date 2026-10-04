/**
 * Admin Bundles page tests
 * Covers: list bundles, new bundle form, create bundle, delete bundle.
 */
import { test, expect } from "@playwright/test";
import { AdminMockApi } from "./mock-admin-api";

test.describe("Bundles page", () => {
  test("lists existing bundles", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/bundles");
    await expect(page.locator("h1")).toContainText(/Bundles/i);
    await expect(page.locator("text=Year 1 Onboarding")).toBeVisible();
  });

  test("shows empty state when no bundles exist", async ({ page }) => {
    const mock = new AdminMockApi({ bundles: [] });
    await mock.attach(page);

    await page.goto("/admin/bundles");
    await expect(page.locator("text=/No bundles yet/i")).toBeVisible();
  });

  test("new bundle form panel is always visible (no create button needed)", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/bundles");
    // The form is a persistent side panel, no button click required
    await expect(page.locator("text=New Bundle")).toBeVisible();
    await expect(page.locator("form input[required]").first()).toBeVisible();
  });

  test("submitting new bundle form calls POST /api/bundles/create", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/bundles");
    const nameInput = page.locator("form input[required]").first();
    await expect(nameInput).toBeVisible();
    await nameInput.fill("Test Bundle");
    await page.locator("form button[type=submit]").click();
    await expect(page.locator("text=Test Bundle")).toBeVisible();
    expect(mock.calls["POST /api/bundles/create"]).toBe(1);
  });

  test("delete bundle calls DELETE /api/bundles/{id}/delete (with native confirm dialog)", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    // Accept the browser's native confirm() dialog
    page.on("dialog", (dialog) => dialog.accept());

    await page.goto("/admin/bundles");
    await expect(page.locator("text=Year 1 Onboarding")).toBeVisible();
    await page.locator("button", { hasText: "Delete" }).first().click();
    await expect(page.locator("text=Year 1 Onboarding")).not.toBeVisible({ timeout: 3000 });
    expect(mock.calls["DELETE /api/bundles/1/delete"]).toBe(1);
  });

  test("bundle card shows role type", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/bundles");
    await expect(page.locator("text=/student/i").first()).toBeVisible();
  });
});
