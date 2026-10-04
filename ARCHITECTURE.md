# Architecture

## System layout
- `apps/web`: operator/admin dashboard
- `apps/api`: Django REST API, workflow orchestration, persistence
- `apps/worker`: Celery execution for async and retryable Google write operations
- `packages/shared`: shared contracts placeholder

## Runtime delivery
- The backend container serves Django admin static assets directly so `/django-admin/` remains usable when `DEBUG=False`.

## Domain flows

### MVP core: timetable publishing (implemented)
1. Operator authenticates with Google Workspace.
2. Operator imports or edits session data.
3. API persists sessions/drafts and queues Meet/publish tasks.
4. Worker executes Calendar/Classroom writes.
5. API stores post/log outcomes.

### Directory sync foundation (implemented)
1. Operator triggers `/api/directory/sync`.
2. Backend iterates Google Admin Directory users page-by-page (no first-page-only totals).
3. `DirectoryUser` cache is upserted with normalized searchable fields.
4. `DirectorySyncJob` stores cumulative fetch/upsert progress and final summary.
5. `/api/directory/stats` returns authoritative totals and running/completed sync status.

### Bulk directory verification (implemented)
1. Operator uploads CSV/XLSX to `/api/directory/verify-upload`.
2. Backend returns header analysis + suggested mapping or runs verification when mapping is provided.
3. Verification engine matches rows against local `DirectoryUser` indexes (not Google per row).
4. `DirectoryVerifyJob` + `DirectoryVerifyRow` persist results and verdicts.
5. Operator reviews paginated rows and exports CSV/XLSX.

## Safety boundaries
- Backend/worker remain the only Google API write path.
- Verification reads local synced directory data only.
- Sync progress (`running`) and completion (`completed`) are explicitly distinct states.
- Totals shown in UI are based on sync-job cumulative counters + DB counts, not page size defaults.
