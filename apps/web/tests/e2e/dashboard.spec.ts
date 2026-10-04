import { expect, Page, test } from "@playwright/test";

import { buildSession, MockApi } from "./mock-api";

async function openApp(page: Page, mockApi: MockApi) {
  await mockApi.attach(page);
  await page.goto("/");
}

async function fillSessionForm(page: Page, title: string) {
  await page.getByLabel("Session course").selectOption("1");
  await page.getByLabel("Session date").fill("2026-03-12");
  await page.getByLabel("Session start time").fill("09:00");
  await page.getByLabel("Session end time").fill("10:00");
  await page.getByLabel("Session title").fill(title);
  await page.getByLabel("Session topic").fill("Autonomic Nervous System");
  await page.getByLabel("Session subject").fill("Physiology");
  await page.getByLabel("Session group").fill("MBBS-1");
}

test("shows the login gate and starts OAuth", async ({ page }) => {
  const mockApi = new MockApi({ auth: { authenticated: false } });

  await openApp(page, mockApi);

  await expect(page.getByText("Classroom Schedule Integrator")).toBeVisible();
  await page.getByRole("button", { name: "Login with Google" }).click();
  await page.waitForURL("**/oauth/mock");
  expect(mockApi.authStartCalls).toBe(1);
});

test("syncs classrooms and filters sessions by selected course", async ({ page }) => {
  const mockApi = new MockApi({
    sessions: [
      buildSession({ id: 1, course: 1, title: "Signals" }),
      buildSession({ id: 2, course: 2, title: "Biochemistry Intro", meet_required: false }),
    ],
  });

  await openApp(page, mockApi);

  await expect(page.locator("h1", { hasText: "Dashboard" })).toBeVisible({ timeout: 10000 });
  await page.getByRole("button", { name: "Sync Classrooms" }).click();
  await expect(page.locator('[aria-label="Course filter"] option')).toContainText(["Pharmacology"]);

  await page.getByLabel("Course filter").selectOption("2");
  await expect(page.getByText("Biochemistry Intro")).toBeVisible();
  await expect(page.getByText("Signals")).toHaveCount(0);
});

test("creates a session from the session manager form", async ({ page }) => {
  const mockApi = new MockApi();

  await openApp(page, mockApi);
  await fillSessionForm(page, "New Seminar");
  await page.getByRole("button", { name: "Add Session" }).click();

  await expect(page.getByText("New Seminar")).toBeVisible();
  expect(mockApi.sessions).toHaveLength(1);
});

test("edits and deletes an existing session", async ({ page }) => {
  const mockApi = new MockApi({
    sessions: [buildSession({ id: 11, title: "Original Title" })],
  });

  await openApp(page, mockApi);

  await page.getByRole("button", { name: "Edit" }).click();
  await page.getByLabel("Session title").fill("Updated Title");
  await page.getByRole("button", { name: "Save Session" }).click();
  await expect(page.getByText("Updated Title")).toBeVisible();

  await page.getByRole("button", { name: "Delete" }).click();
  await expect(page.getByText("Updated Title")).toHaveCount(0);
  expect(mockApi.sessions).toHaveLength(0);
});

test("generates meet links and surfaces them in the table and logs", async ({ page }) => {
  const mockApi = new MockApi({
    sessions: [buildSession({ id: 21, title: "Meet Session" })],
  });

  await openApp(page, mockApi);

  await page.getByLabel("Select session Meet Session").check();
  await page.getByRole("button", { name: "Generate Meet Links" }).click();

  await expect(page.getByRole("link", { name: "Open link" })).toHaveAttribute(
    "href",
    "https://meet.google.com/test-21",
  );
  await expect(page.getByText("Meet link generated")).toBeVisible();
});

test("schedules selected posts and updates status to scheduled", async ({ page }) => {
  const mockApi = new MockApi({
    sessions: [buildSession({ id: 31, title: "Scheduled Session" })],
  });

  await openApp(page, mockApi);

  await page.getByLabel("Select session Scheduled Session").check();
  await page.getByRole("button", { name: "Schedule Posts" }).click();

  await expect(page.locator("tbody tr", { hasText: "Scheduled Session" }).getByText("scheduled")).toBeVisible();
  await expect(page.getByText("Classroom post created")).toBeVisible();
  expect(mockApi.sessions[0].meet_link).toBe("https://meet.google.com/test-31");
});

test("publishes immediately and ensures meet-required sessions end with a meet link", async ({ page }) => {
  const mockApi = new MockApi({
    sessions: [buildSession({ id: 41, title: "Publish Session", meet_link: "", calendar_event_id: "" })],
  });

  await openApp(page, mockApi);

  await page.getByLabel("Select session Publish Session").check();
  await page.getByRole("button", { name: "Publish Now" }).click();

  await expect(page.locator("tbody tr", { hasText: "Publish Session" }).getByText("posted")).toBeVisible();
  await expect(page.getByRole("link", { name: "Open link" })).toHaveAttribute(
    "href",
    "https://meet.google.com/test-41",
  );
  await expect(page.getByText("Classroom post created")).toBeVisible();
});

test("shows not required for sessions that do not need a meet link", async ({ page }) => {
  const mockApi = new MockApi({
    sessions: [buildSession({ id: 51, title: "Offline Session", meet_required: false })],
  });

  await openApp(page, mockApi);

  await expect(page.getByText("Not required")).toBeVisible();
  await page.getByLabel("Select session Offline Session").check();
  await page.getByRole("button", { name: "Publish Now" }).click();
  await expect(page.locator("tbody tr", { hasText: "Offline Session" }).getByText("posted")).toBeVisible();
  await expect(page.getByText("Not required")).toBeVisible();
});
