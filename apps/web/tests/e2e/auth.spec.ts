/**
 * Auth redirect + logout tests
 * Verifies that unauthenticated users are redirected to login,
 * and that the logout button works from the sidebar.
 */
import { test, expect } from "@playwright/test";
import { AdminMockApi } from "./mock-admin-api";

test.describe("Auth redirect behavior", () => {
  test("unauthenticated user visiting /admin/groups is redirected to /", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: false });
    await mock.attach(page);

    await page.goto("/admin/groups");
    await page.waitForURL("/");
    await expect(page).toHaveURL("/");
  });

  test("unauthenticated user visiting /imports is redirected to /", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: false });
    await mock.attach(page);

    await page.goto("/imports");
    await page.waitForURL("/");
    await expect(page).toHaveURL("/");
  });

  test("unauthenticated user visiting /publish is redirected to /", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: false });
    await mock.attach(page);

    await page.goto("/publish");
    await page.waitForURL("/");
    await expect(page).toHaveURL("/");
  });

  test("unauthenticated user visiting /admin/courses is redirected to /", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: false });
    await mock.attach(page);

    await page.goto("/admin/courses");
    await page.waitForURL("/");
    await expect(page).toHaveURL("/");
  });

  test("authenticated user visiting /admin/groups sees the page (not redirected)", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: true });
    await mock.attach(page);

    await page.goto("/admin/groups");
    await expect(page.locator("h1")).toContainText("Google Groups");
  });
});

test.describe("Sidebar", () => {
  test("sidebar is visible on admin pages when authenticated", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: true });
    await mock.attach(page);

    await page.goto("/admin/groups");
    await expect(page.locator("aside")).toBeVisible();
  });

  test("sidebar shows user email", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: true, userEmail: "admin@school.org" });
    await mock.attach(page);

    await page.goto("/admin/groups");
    await expect(page.locator("aside")).toContainText("admin@school.org");
  });

  test("sidebar contains navigation links", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: true });
    await mock.attach(page);

    await page.goto("/admin/groups");
    const sidebar = page.locator("aside");
    await expect(sidebar.locator("a", { hasText: "Dashboard" })).toBeVisible();
    await expect(sidebar.locator("a", { hasText: "Groups" })).toBeVisible();
    await expect(sidebar.locator("a", { hasText: "Courses" })).toBeVisible();
    await expect(sidebar.locator("a", { hasText: "Bundles" })).toBeVisible();
    await expect(sidebar.locator("a", { hasText: "Commands" })).toBeVisible();
    await expect(sidebar.locator("a", { hasText: "Jobs" })).toBeVisible();
  });

  test("logout button calls /api/auth/logout and redirects to /", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: true });
    await mock.attach(page);

    await page.goto("/admin/groups");
    const logoutBtn = page.locator("aside button", { hasText: /Logout/i });
    await expect(logoutBtn).toBeVisible();
    await logoutBtn.click();
    await page.waitForURL("/");
    await expect(page).toHaveURL("/");
    expect(mock.calls["POST /api/auth/logout"]).toBe(1);
  });
});

test.describe("Login page (unauthenticated /)", () => {
  test("shows Login with Google button when not authenticated", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: false });
    await mock.attach(page);

    await page.goto("/");
    await expect(page.locator("button", { hasText: /Login with Google/i })).toBeVisible();
  });

  test("clicking login button calls /api/auth/google/start", async ({ page }) => {
    const mock = new AdminMockApi({ authenticated: false });
    await mock.attach(page);

    await page.goto("/");
    await page.locator("button", { hasText: /Login with Google/i }).click();
    // Should redirect to OAuth mock URL
    await expect(page).toHaveURL(/oauth\/mock/);
  });
});
