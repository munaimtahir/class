# class

`class` is a focused academic operations platform for Google Workspace and Google Classroom workflows.

It is **not** a full LMS.

## Product scope at a glance
- **MVP core (implemented):** import timetable/session data, review/edit sessions, generate Meet links, publish or schedule Classroom posts, track logs/retries.
- **Bounded expansion (implemented):** **Directory Verification** for full local directory sync, bulk CSV/XLSX verification, and exportable verification results.
- **Future adjacent modules (roadmap only):** broader Enrollment Management and Smarter Publishing Controls.

## MVP core capabilities (implemented)
- Google OAuth login with backend-owned credentials/tokens
- Classroom course sync
- Session CRUD
- Google Sheet import preview, commit, and promotion
- Meet generation via Calendar API
- Classroom posting (immediate and scheduled)
- Combined-day announcement preview and publish
- Posting logs and duplicate-aware import behavior

## Directory Verification module (implemented)
The directory module supports operational verification workflows without per-row Google lookups:
- full paginated Google Workspace user sync into local `DirectoryUser` cache
- authoritative sync job tracking (`DirectorySyncJob`) with cumulative page/fetch/upsert counts
- sync stats endpoint for accurate total user counts and running/completed sync state
- CSV/XLSX upload and flexible header mapping for verification
- row-wise verdicts: `exists`, `does_not_exist`, `ambiguous`, `invalid_input`
- results export as CSV and XLSX

## Explicitly out of scope
- Attendance, grading, exams, and student analytics
- Student/parent portals
- Generic institutional ERP workflows
- General IT helpdesk complaints not tied to the app’s Google Workspace/Classroom operations

## Safety model
- Backend and worker layers own all Google write operations.
- Resolution actions must remain auditable and linked to operator context.
- Retry-safe, idempotent execution is required for write paths.
- Local DB stores workflow state; Google remains source of truth for account/classroom reality.

## Stack
- Frontend: Next.js + React + TypeScript + TailwindCSS
- Backend: Django + Django REST Framework
- Database: PostgreSQL
- Async jobs: Celery + Redis
- Google APIs: Classroom, Calendar, Sheets

## Monorepo structure
- `apps/api`: Django API, Google integrations, import logic, models, Celery tasks
- `apps/web`: Next.js operator dashboard
- `apps/worker`: worker container support
- `packages/shared`: shared-contract placeholder

## Core API surface (implemented)
- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `GET /api/auth/status`
- `POST /api/auth/logout`
- `GET /api/classrooms/`
- `GET /api/classrooms/sync/`
- `GET|POST /api/sessions/`
- `GET|PATCH|DELETE /api/sessions/{id}/`
- `POST /api/sessions/generate-meet/`
- `POST /api/sessions/schedule-posts/`
- `POST /api/sessions/publish-now/`
- `POST /api/imports/google-sheet/preview`
- `POST /api/imports/google-sheet/commit`
- `GET /api/imports/`
- `GET /api/imports/{id}/`
- `POST /api/imports/{id}/promote/`
- `POST /api/publish/combined-day-preview`
- `POST /api/publish/combined-day-post`
- `GET /api/logs/`

## Google scope management (implemented)
- Canonical backend scope registry and feature-to-scope mapping are centralized in one module.
- Protected actions validate required scopes before any Google API call.
- Missing permission responses are structured (`code=GOOGLE_SCOPE_MISSING`) with:
  - `feature`
  - `missingScopes`
  - `reauthorizeUrl`
- Operators can reconnect or upgrade permissions via auth start modes:
  - default connect: `/api/auth/google/start`
  - reconnect full consent: `/api/auth/google/start?mode=reconnect`
  - targeted upgrade: `/api/auth/google/start?mode=upgrade&upgrade=<feature>`
- OAuth callback persists normalized scope metadata for future checks.

## Recovering from permission errors
1. Trigger the blocked action from the UI.
2. Use the provided reconnect/upgrade button.
3. Complete Google consent and return to the app.
4. Retry the original action.

## Directory Verification API families (implemented)
- `/api/directory/sync`
- `/api/directory/sync-jobs*`
- `/api/directory/stats`
- `/api/directory/verify-upload`
- `/api/directory/verify-jobs*`

## Quick start
1. Copy env templates and configure Google credentials/scopes.
2. Start services with Docker Compose.
3. Open the web app and authenticate with an operator account.

## Notes
- Frontend never stores refresh tokens.
- Refresh tokens are encrypted at rest.
- Google write actions execute via backend/worker flows only.
- Backend serves Django admin static assets from Django so `/django-admin/` stays usable in deployed environments.
