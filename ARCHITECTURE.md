# ARCHITECTURE.md

## High-level architecture
- `apps/web`: Next.js admin dashboard
- `apps/api`: Django REST backend
- `apps/worker`: Celery worker for scheduled publishing and retries
- `packages/shared`: shared schemas, sample payload contracts, constants

## Flow
1. User authenticates with Google.
2. Backend stores connection metadata securely.
3. User imports sessions.
4. Backend stores session drafts.
5. User triggers preview/publish.
6. Backend queues publish job.
7. Worker performs Google Calendar + Classroom calls.
8. Results are stored in publish logs.
9. UI shows final status.

## Key design choices
- all Google API writes happen in backend/worker only
- frontend never handles raw Google tokens for publishing logic
- publish operations are idempotent
- dry-run preview precedes publish
