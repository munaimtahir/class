# Final AI Developer Prompt

Build and maintain `class` as a focused institutional operations platform.

## Product definition
- **MVP core (implemented):** timetable/session import, review, Meet generation, Classroom publish/schedule, and publish logging.
- **Official expansion scope:** **Stage 3A — User Operations and Resolution** via the **User Resolution Center**.
- **Future adjacent modules (roadmap):** Directory Management, Enrollment Management, Smarter Publishing Controls.

This product is operational tooling, not a full LMS and not a generic IT helpdesk.

## MVP baseline to preserve
- Google OAuth login and backend token handling
- Classroom course sync
- Session CRUD
- Google Sheet import preview/commit/promote flow
- Meet generation
- Classroom publish-now/schedule flows
- Combined-day preview/publish
- Posting logs and worker execution

## Stage 3A target capabilities (User Resolution Center)
- Issue intake for bounded operational categories
- Issue list/detail workflow with filters and linked operational context
- Assignment, comments, diagnostics timeline
- Resolution and escalation lifecycle with explicit status transitions
- Dashboard summaries for queue monitoring
- Action logging/auditability for issue-state and resolution events

## Mandatory scope boundaries
- In scope: issues tied to Google account readiness, Classroom access/enrollment, course/session mapping, Meet generation, publish outcomes, and related operational blockers.
- Out of scope: grading, attendance, exams, analytics portals, generic ERP workflows, unrelated IT/helpdesk complaints.

## Safety and control requirements
- Backend/worker owns all Google write operations.
- Reuse existing publish/retry safety patterns for issue-triggered operational actions.
- Keep write paths idempotent and retry-safe.
- Every high-impact action must produce traceable logs with actor and timestamps.
- Local DB acts as workflow state; Google remains source of truth.

## Architecture requirements
- Keep a single API boundary (web -> backend API -> worker for async writes).
- Link issue records to existing operational entities where relevant (`user`, `course`, `session`, `post`, `log`).
- Avoid frontend-managed secrets or direct Google write calls.

## Implementation requirements
- Add typed models/serializers for issues, categories, assignments, comments, resolutions, attachments, and action logs.
- Add list/create/view/update/assign/comment/resolve/escalate APIs with strict state validation.
- Add tests for issue lifecycle, linking, role boundaries, and dashboard summaries.
- Update docs (`README`, architecture, API, data model, tasks, tests, QA) with each meaningful change.
- Keep terminology consistent across docs: **User Resolution Center** and **Stage 3A — User Operations and Resolution**.

## Explicit non-goals
- Full LMS feature expansion
- Student/parent portals
- Generic institutional helpdesk intake
- Unbounded ERP process orchestration
