# Multi-Stage Development Roadmap

## Stage 1 — Foundation / MVP
Goal: deliver a working internal tool for timetable-to-Classroom publishing.

### Deliverables
- repo initialized
- Google OAuth login
- Google Classroom course fetch
- session CRUD
- simple import parser (CSV/Google Sheet/manual)
- Calendar event + Meet link generation
- Classroom material creation
- schedule-or-publish workflow
- posting log

### Acceptance
- user can import 1 day timetable
- preview/edit sessions
- publish to selected course
- see success/failure per session

## Stage 2 — Reliability and usability
Goal: make the MVP safe for repeated weekly use.

### Deliverables
- duplicate detection rules
- retry failed items
- topic templates by week/day
- basic audit trail
- import validation
- bulk publish by day/week
- safer idempotency logic

### Acceptance
- repeated import of same timetable does not double-post
- failed jobs can be retried
- user can publish a whole day in one action

## Stage 3 — Operational expansion
Goal: reduce more manual work.

### Deliverables
- direct Google Sheets sync
- saved publishing templates
- subgroup rules
- role-based access for admin/operators
- better monitoring dashboard

## Stage 4 — Institutional productization
Goal: make it reusable across departments/institutions.

### Deliverables
- multi-tenant support
- faculty-specific publishing rules
- reusable timetable presets
- analytics and reporting
