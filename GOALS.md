# Goals

## Product outcome
Provide one institutional operations platform with:
- a stable MVP timetable publishing core
- a bounded operational resolution module: **User Resolution Center** in **Stage 3A — User Operations and Resolution**

## MVP core goals
- Keep timetable publishing fast and reliable for weekly academic operations.
- Prevent duplicate import/publish behavior through deterministic checks.
- Provide clear publish status, logs, and retry visibility per session.
- Preserve backend/worker ownership of all Google write operations.

## Stage 3A goals (User Resolution Center)
- Capture operational user issues in a structured, trackable workflow.
- Support assignment, diagnosis, escalation, and resolution with auditable history.
- Link issues to relevant users, courses, sessions, Meet records, and publish logs.
- Reduce resolution time for platform-blocking incidents in Google Workspace/Classroom workflows.
- Keep issue categories bounded to operational scope and prevent general helpdesk sprawl.

## In-scope issue types
- Institutional email readiness/access for platform use
- Classroom enrollment missing/wrong
- Faculty permission/access blocking course operations
- Course/session/timetable mapping issues
- Missing Meet links
- Publish failures and related user access blockers
- Wrong/duplicate account mapping that impacts platform operations

## Cross-module success criteria
- MVP publishing workflows remain stable while Stage 3A expands support capability.
- Issue state transitions are explicit and audit-friendly.
- Operator and admin responsibilities remain clear.
- Documentation, API contracts, data model docs, tasks, tests, and QA checks stay aligned.

## Non-goals
- Full LMS functionality (grading, attendance, exams, analytics).
- Student/parent portal expansion.
- Generic institutional ERP workflows.
- Unbounded IT helpdesk complaint intake unrelated to app operations.
