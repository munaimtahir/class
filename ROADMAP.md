# Roadmap

## Stage 1 - MVP publishing foundation (implemented)
Goal: reliable timetable-to-Classroom publishing with Meet integration.

Delivered:
- Google OAuth login with backend-owned tokens
- Classroom course sync
- Session CRUD
- Google Sheet import preview, commit, and promotion flow
- Meet generation via Calendar API
- Classroom material publishing
- Scheduled posting via worker
- Combined-day preview and publish
- Posting logs

## Stage 2 - MVP reliability hardening (active)
Goal: improve repeatability, safety, and observability of timetable operations.

Deliverables:
- Close remaining test and integration gaps
- Improve retry/error visibility in publish flows
- Tighten idempotency semantics for recurring imports and publishes
- Keep docs aligned with implemented behavior

## Stage 3A — User Operations and Resolution (official next scope)
Goal: add a bounded **User Resolution Center** for operational issue handling tied to Google Workspace/Classroom workflows.

Planned deliverables:
- Structured issue intake with bounded categories
- Issue list/detail workflow with assignment and collaboration
- Diagnosis workflow linked to session/publish operational records
- Resolution and escalation lifecycle with clear status transitions
- Dashboard views for open/resolved/escalated queues and counts
- Action logging/auditability for issue-state and resolution actions

## Stage 3B - Directory Management (future adjacent module)
Goal: add controlled directory governance workflows where needed.

## Stage 3C - Enrollment Management (future adjacent module)
Goal: add bounded enrollment operations for Classroom course membership.

## Stage 3D - Smarter Publishing Controls (future adjacent module)
Goal: improve publish planning, guardrails, and operator controls without expanding into LMS behavior.
