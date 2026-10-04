/**
 * Admin Groups page tests
 * Covers: list groups, sync groups, view members, add member, remove member.
 */
import { test, expect } from "@playwright/test";
import { AdminMockApi } from "./mock-admin-api";

test.describe("Groups page", () => {
  test("displays synced groups in a table", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    await expect(page.locator("h1")).toContainText("Google Groups");
    await expect(page.locator("td", { hasText: "Year 1 Students" })).toBeVisible();
    await expect(page.locator("td", { hasText: "Teaching Staff" })).toBeVisible();
  });

  test("shows placeholder when no groups are synced", async ({ page }) => {
    const mock = new AdminMockApi({ groups: [] });
    await mock.attach(page);

    await page.goto("/admin/groups");
    await expect(page.locator("text=No groups synced yet")).toBeVisible();
  });

  test("sync button calls /api/groups/sync and shows success message", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    const syncBtn = page.locator("button", { hasText: /Sync from Google/i });
    await expect(syncBtn).toBeVisible();
    await syncBtn.click();
    await expect(page.locator("text=/Synced:/i")).toBeVisible();
    expect(mock.calls["POST /api/groups/sync"]).toBe(1);
  });

  test("clicking Members button loads member list for that group", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    const membersBtn = page.locator("button", { hasText: "Members" }).first();
    await membersBtn.click();
    await expect(page.locator("text=student1@school.org")).toBeVisible();
    await expect(page.locator("text=student2@school.org")).toBeVisible();
  });

  test("add member form submits POST /api/groups/add-member", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    // Open members panel first
    await page.locator("button", { hasText: "Members" }).first().click();
    await expect(page.locator("input[type=email]")).toBeVisible();

    // Select "Add member" action (should already be selected by default)
    await page.locator("select").selectOption("add");
    await page.locator("input[type=email]").fill("newstudent@school.org");
    await page.locator("button", { hasText: /^Add$/ }).click();
    await expect(page.locator("text=/Added newstudent/i")).toBeVisible();
    expect(mock.calls["POST /api/groups/add-member"]).toBe(1);
  });

  test("remove member form submits POST /api/groups/remove-member", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    await page.locator("button", { hasText: "Members" }).first().click();
    await expect(page.locator("input[type=email]")).toBeVisible();

    // Select remove action and fill in the email input
    await page.locator("select").selectOption("remove");
    await page.locator("input[type=email]").fill("student1@school.org");
    // Click the form submit button (the large one next to the email input, styled with red bg)
    // Use the button that's a sibling of the email input inside the flex row
    await page.locator("input[type=email] + button, input[type=email] ~ button").first().click();
    await expect(page.locator("text=/Removed student1/i")).toBeVisible();
    expect(mock.calls["POST /api/groups/remove-member"]).toBe(1);
  });

  test("clicking quick-remove button in member list pre-fills remove form", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    await page.locator("button", { hasText: "Members" }).first().click();
    // Click the inline Remove button for student1
    await page.locator("li").filter({ hasText: "student1@school.org" }).locator("button", { hasText: "Remove" }).click();
    // The email input should now contain that email
    await expect(page.locator("input[type=email]")).toHaveValue("student1@school.org");
    // And the action should be "remove"
    await expect(page.locator("select")).toHaveValue("remove");
  });

  test("closing the member panel hides it", async ({ page }) => {
    const mock = new AdminMockApi();
    await mock.attach(page);

    await page.goto("/admin/groups");
    await page.locator("button", { hasText: "Members" }).first().click();
    await expect(page.locator("input[type=email]")).toBeVisible();
    await page.locator("button", { hasText: "×" }).click();
    await expect(page.locator("input[type=email]")).not.toBeVisible();
  });
});
