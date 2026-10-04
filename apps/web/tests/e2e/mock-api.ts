import { Page, Route } from "@playwright/test";

type AuthState = {
  authenticated: boolean;
  user?: { name: string; email: string };
};

export type MockCourse = {
  id: number;
  google_course_id: string;
  name: string;
  section: string;
};

export type MockSession = {
  id: number;
  course: number;
  date: string;
  start_time: string;
  end_time: string;
  title: string;
  topic: string;
  subject: string;
  group: string;
  meet_required: boolean;
  post_type: "material" | "announcement";
  status: string;
  meet_link: string;
  calendar_event_id: string;
};

export type MockLog = {
  id: number;
  session: number;
  status: string;
  message: string;
  created_at: string;
};

type MockApiOptions = {
  auth?: AuthState;
  courses?: MockCourse[];
  sessions?: MockSession[];
  logs?: MockLog[];
};

function json(route: Route, body: unknown, status = 200) {
  return route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify(body),
  });
}

export class MockApi {
  auth: AuthState;
  courses: MockCourse[];
  sessions: MockSession[];
  logs: MockLog[];
  authStartCalls = 0;
  syncCalls = 0;
  private nextSessionId: number;
  private nextLogId: number;

  constructor(options: MockApiOptions = {}) {
    this.auth = options.auth ?? {
      authenticated: true,
      user: { name: "QA User", email: "qa@example.com" },
    };
    this.courses = options.courses ?? [
      { id: 1, google_course_id: "course-1", name: "Physiology", section: "A" },
      { id: 2, google_course_id: "course-2", name: "Biochemistry", section: "B" },
    ];
    this.sessions = options.sessions ?? [];
    this.logs = options.logs ?? [];
    this.nextSessionId = Math.max(0, ...this.sessions.map((session) => session.id)) + 1;
    this.nextLogId = Math.max(0, ...this.logs.map((log) => log.id)) + 1;
  }

  async attach(page: Page) {
    await page.route("**/api/**", async (route) => {
      const url = new URL(route.request().url());
      const pathname = url.pathname;
      const method = route.request().method();

      if (pathname === "/api/auth/status" && method === "GET") {
        return json(route, this.auth);
      }

      if (pathname === "/api/auth/google/start" && method === "GET") {
        this.authStartCalls += 1;
        return json(route, { auth_url: `${url.origin}/oauth/mock` });
      }

      if (pathname === "/api/auth/logout" && method === "POST") {
        this.auth = { authenticated: false };
        return json(route, { ok: true });
      }

      if (pathname === "/api/classrooms/" && method === "GET") {
        return json(route, this.courses);
      }

      if (pathname === "/api/classrooms/sync/" && method === "GET") {
        this.syncCalls += 1;
        const exists = this.courses.some((course) => course.google_course_id === "course-3");
        if (!exists) {
          this.courses.push({
            id: 3,
            google_course_id: "course-3",
            name: "Pharmacology",
            section: "C",
          });
        }
        return json(route, { synced: this.courses.length, created: exists ? 0 : 1 });
      }

      if (pathname === "/api/sessions/" && method === "GET") {
        return json(route, this.sessions);
      }

      if (pathname === "/api/logs/" && method === "GET") {
        return json(route, this.logs);
      }

      if (pathname === "/api/sessions/" && method === "POST") {
        const payload = route.request().postDataJSON() as Omit<MockSession, "id" | "status" | "meet_link" | "calendar_event_id">;
        const session: MockSession = {
          ...payload,
          id: this.nextSessionId++,
          status: "pending",
          meet_link: "",
          calendar_event_id: "",
        };
        this.sessions.push(session);
        return json(route, session, 201);
      }

      if (pathname === "/api/sessions/generate-meet/" && method === "POST") {
        const { session_ids } = route.request().postDataJSON() as { session_ids: number[] };
        for (const id of session_ids) {
          const session = this.sessions.find((entry) => entry.id === id);
          if (!session || !session.meet_required) {
            continue;
          }
          session.meet_link = `https://meet.google.com/test-${id}`;
          session.calendar_event_id = `event-${id}`;
          this.pushLog(session.id, session.status, "Meet link generated");
        }
        return json(route, { queued: session_ids.length });
      }

      if (pathname === "/api/sessions/schedule-posts/" && method === "POST") {
        const { session_ids } = route.request().postDataJSON() as { session_ids: number[] };
        for (const id of session_ids) {
          const session = this.sessions.find((entry) => entry.id === id);
          if (!session) {
            continue;
          }
          if (session.meet_required && !session.meet_link) {
            session.meet_link = `https://meet.google.com/test-${id}`;
            session.calendar_event_id = `event-${id}`;
          }
          session.status = "scheduled";
          this.pushLog(session.id, "scheduled", "Classroom post created");
        }
        return json(route, { scheduled: session_ids.length });
      }

      if (pathname === "/api/sessions/publish-now/" && method === "POST") {
        const { session_ids } = route.request().postDataJSON() as { session_ids: number[] };
        for (const id of session_ids) {
          const session = this.sessions.find((entry) => entry.id === id);
          if (!session) {
            continue;
          }
          if (session.meet_required && !session.meet_link) {
            session.meet_link = `https://meet.google.com/test-${id}`;
            session.calendar_event_id = `event-${id}`;
          }
          session.status = "posted";
          this.pushLog(session.id, "posted", "Classroom post created");
        }
        return json(route, { queued: session_ids.length });
      }

      const sessionMatch = pathname.match(/^\/api\/sessions\/(\d+)\/$/);
      if (sessionMatch && method === "PATCH") {
        const id = Number(sessionMatch[1]);
        const session = this.sessions.find((entry) => entry.id === id);
        if (!session) {
          return json(route, { detail: "Not found" }, 404);
        }
        Object.assign(session, route.request().postDataJSON());
        return json(route, session);
      }

      if (sessionMatch && method === "DELETE") {
        const id = Number(sessionMatch[1]);
        this.sessions = this.sessions.filter((entry) => entry.id !== id);
        this.logs = this.logs.filter((entry) => entry.session !== id);
        return route.fulfill({ status: 204, body: "" });
      }

      return json(route, { detail: `Unhandled route: ${method} ${pathname}` }, 500);
    });

    await page.route("**/oauth/mock", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "text/html",
        body: "<html><body><h1>Mock OAuth</h1></body></html>",
      });
    });
  }

  pushLog(sessionId: number, status: string, message: string) {
    this.logs.unshift({
      id: this.nextLogId++,
      session: sessionId,
      status,
      message,
      created_at: new Date().toISOString(),
    });
  }
}

export function buildSession(overrides: Partial<MockSession> = {}): MockSession {
  return {
    id: overrides.id ?? 1,
    course: overrides.course ?? 1,
    date: overrides.date ?? "2026-03-10",
    start_time: overrides.start_time ?? "09:40",
    end_time: overrides.end_time ?? "10:40",
    title: overrides.title ?? "Processing of Signals",
    topic: overrides.topic ?? "CNS",
    subject: overrides.subject ?? "Physiology",
    group: overrides.group ?? "A1",
    meet_required: overrides.meet_required ?? true,
    post_type: overrides.post_type ?? "material",
    status: overrides.status ?? "pending",
    meet_link: overrides.meet_link ?? "",
    calendar_event_id: overrides.calendar_event_id ?? "",
  };
}
