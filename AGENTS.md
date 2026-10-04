# AGENTS.md

## Purpose
This repository is `class`, a Google Workspace/Classroom operations app with clear scope boundaries:

- MVP core is implemented: timetable-to-Google-Classroom publishing.
- The official next expansion is **Stage 3A — User Operations and Resolution** via the **User Resolution Center**.
- Future adjacent modules remain roadmap items: Directory Management, Enrollment Management, Smarter Publishing Controls.

Agents working in this repo must keep implemented scope, active expansion scope, and future roadmap clearly separated.

## Source of truth
Before making product or architecture decisions, read:

- `README.md`
- `ROADMAP.md`
- `TASKS.md`
- `ARCHITECTURE.md`
- `API_INTERFACES.md`
- `DATAMODEL.md`
- `AGENT.md`

If code and docs disagree, treat code as truth for implemented behavior and label planned work explicitly.

## Current implemented scope (MVP core)
- Google OAuth login with backend-owned tokens
- Classroom course sync
- Session CRUD
- Google Sheet import preview, commit, and promote flow
- Meet creation via Google Calendar
- Classroom material publishing
- Combined-day announcement preview and publish
- Celery-backed scheduled posting
- Posting logs and import dedupe behavior

## Active expansion scope (Stage 3A)
The User Resolution Center handles bounded operational user issues related to:
- Google account readiness/access for institutional use
- Classroom access and enrollment correctness
- course/session mapping and timetable workflow issues
- Meet generation and publish outcomes
- account mapping conflicts affecting workflow access

This is not a general helpdesk system.

## Product guardrails
- Preserve the existing timetable publishing workflow.
- Do not add unrelated LMS features.
- Do not add generic helpdesk/ERP complaint handling.
- Keep backend or worker layers as the only place where Google write operations occur.
- Prefer preview-before-run flows for high-impact operations.
- All Google-side effects and issue-state actions must be logged.
- Favor retry-safe and idempotent behavior.
- Keep credentials and scopes in environment variables.

## Repository map
- `apps/api`: Django API, Google integrations, import logic, models, Celery tasks
- `apps/web`: Next.js operator dashboard
- `apps/worker`: worker container support
- `packages/shared`: shared-contract placeholder

## Implementation guidance

### For MVP core work
- Extend existing session, import, publish, and logging patterns.
- Reuse current Celery task flow for asynchronous Google operations.
- Keep API docs aligned with real routes and serializers.

### For Stage 3A work
- Build issue workflows on existing backend/worker patterns.
- Link issue records to users/courses/sessions/publish logs where relevant.
- Add assignment, comments, resolution, and escalation with explicit state transitions.
- Keep issue categories tightly bounded to operational scope.

### For future modules
- Keep Directory Management, Enrollment Management, and Smarter Publishing Controls labeled as roadmap items until implemented.

## Documentation rules
- Update `README.md`, `TASKS.md`, and affected architecture/API/data-model docs when behavior changes.
- Mark roadmap items clearly as planned until merged into code.
- Keep module/stage naming consistent:
  - **User Resolution Center**
  - **Stage 3A — User Operations and Resolution**

## Verification rules
Before claiming work complete:

- confirm routes exist for claimed implemented APIs
- confirm models and migrations exist where required
- confirm worker tasks execute intended flows
- confirm tests cover behavior changes
- confirm docs reflect actual implementation state

## Forbidden shortcuts
- Do not claim future roadmap features exist unless code is present.
- Do not move Google write logic into the frontend.
- Do not bypass logging for publish or resolution workflows.
- Do not replace existing publish flows when extending the product.
