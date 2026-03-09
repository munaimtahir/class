# Final AI Developer Prompt

Build a production-oriented MVP for **Classroom Schedule Integrator**, a narrow internal web app that converts timetable sessions into scheduled Google Classroom posts with Google Meet links.

## Product goal
Create a reliable internal tool for academic staff to import or enter timetable sessions, review them, generate Meet links through Google Calendar events, publish/schedule Google Classroom materials, and track posting status.

## Scope lock
### Must build
- Google OAuth sign-in for approved Workspace users
- fetch Google Classroom courses user can manage
- session import via CSV and manual entry
- optional Google Sheet import stub/interface
- session preview/edit UI
- create Calendar events with Meet links when required
- create Google Classroom Material posts
- immediate publish or scheduled publish
- posting log with statuses: draft, queued, published, failed, skipped
- idempotency / duplicate prevention
- clean API docs
- tests for main flows

### Must not build in MVP
- attendance
- grading
- student analytics
- submissions
- OCR/image timetable parsing
- full LMS features
- parent/student portals

## Recommended stack
- Frontend: Next.js 14+ with TypeScript
- Backend: Django 5 + DRF
- DB: PostgreSQL
- Worker: Celery + Redis
- Auth: Google OAuth 2.0
- Integrations: Google Classroom API, Google Calendar API, Google Sheets API

## Architecture requirements
- frontend and backend separated by clean API boundary
- backend owns all Google API interactions
- all publish actions logged
- idempotency key per publishable session
- dry-run preview before publish
- use environment variables for secrets
- no hardcoded course IDs or tokens

## Core entities
- User
- WorkspaceConnection
- CourseMap
- ImportBatch
- SessionDraft
- PublishJob
- CalendarEventRecord
- ClassroomPostRecord
- AuditLog

## API requirements
Implement endpoints for:
- auth start/callback/status/logout
- list connected courses
- create/list/update/delete session drafts
- import CSV
- import Google Sheet metadata stub
- preview publish plan
- create publish job
- execute publish job
- list publish logs and failures
- retry failed publish items

## UI requirements
Pages:
- login/connect page
- dashboard
- course selector
- import sessions page
- review sessions page
- publish planner
- posting log page

## Publishing logic
- if `requires_meet = true`, create Calendar event with conference data
- store Meet URL and calendar event ID
- create Classroom material under target course with title/description/Meet link
- scheduled publishing should queue job and execute at intended time
- duplicate prevention should compare course + date + time + title + subgroup + publish mode hash

## Quality bar
- typed code
- clean separation of concerns
- migrations included
- seed/demo data for local testing
- README + setup instructions
- unit tests + integration tests
- graceful error handling around Google API failures
- clear operator messages

## Deliverables
1. working repo scaffold
2. backend API
3. frontend admin panel
4. worker jobs
5. DB schema + migrations
6. tests
7. setup docs
8. sample CSV and sample seed data

## TODO checklist
- [ ] initialize monorepo/repo structure
- [ ] implement Google auth flow
- [ ] fetch and display Classroom courses
- [ ] build session draft data model
- [ ] build CSV import parser
- [ ] build session review table/form
- [ ] implement Calendar event + Meet creation
- [ ] implement Classroom material posting
- [ ] implement scheduled publish job
- [ ] implement posting log and retry flow
- [ ] add idempotency checks
- [ ] write tests and setup docs
