# Classroom Schedule Integrator — AI Dev Pack

This pack is the starting kit for building a narrow internal web application that converts timetable sessions into scheduled Google Classroom posts with Google Meet links and posting logs.

## Included
- Plain-language product brief
- Multi-stage roadmap
- Final autonomous AI developer prompt
- AGENT, GOALS, TESTS, ARCHITECTURE, DATAMODEL, API/Interfaces, Setup, CI/CD, QA, Contributing, Tasks
- Basic repo scaffold
- GitHub issue templates

## Product summary
The application is for academic staff who already prepare a timetable elsewhere and need a reliable way to:
- import or enter sessions
- map them to Google Classroom courses
- generate Google Meet links through Calendar events
- create scheduled Classroom posts
- track what was posted, failed, or skipped

## Suggested repo shape
- `apps/web` — frontend admin dashboard
- `apps/api` — backend API + Google integration
- `apps/worker` — background publishing jobs
- `packages/shared` — shared types/schemas/constants
- `docs` — design/governance notes if expanded later

## Recommended stack
- Frontend: Next.js
- Backend: Django + Django REST Framework
- Worker: Celery or RQ
- Database: PostgreSQL
- Auth: Google OAuth (Workspace)
- Integrations: Google Classroom API, Calendar API, Sheets API
