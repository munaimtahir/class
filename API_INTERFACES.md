# API Interfaces

## MVP core (implemented): timetable publishing

### Auth
- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `GET /api/auth/status`
- `POST /api/auth/logout`

### Courses
- `GET /api/classrooms/`
- `GET /api/classrooms/sync/`

### Sessions
- `GET /api/sessions/`
- `POST /api/sessions/`
- `GET /api/sessions/{id}/`
- `PATCH /api/sessions/{id}/`
- `DELETE /api/sessions/{id}/`
- `POST /api/sessions/generate-meet/`
- `POST /api/sessions/schedule-posts/`
- `POST /api/sessions/publish-now/`

### Imports and publish
- `POST /api/imports/google-sheet/preview`
- `POST /api/imports/google-sheet/commit`
- `GET /api/imports/`
- `GET /api/imports/{id}/`
- `POST /api/imports/{id}/promote/`
- `POST /api/publish/combined-day-preview`
- `POST /api/publish/combined-day-post`
- `GET /api/logs/`

## Directory foundation (implemented)

### Directory users and sync
- `GET /api/directory/users`
- `GET /api/directory/users/{id}`
- `PATCH /api/directory/users/{id}` (local workflow metadata)
- `POST /api/directory/sync`
- `GET /api/directory/sync-jobs`
- `GET /api/directory/sync-jobs/{id}`
- `GET /api/directory/stats`

### Directory verification (implemented)
- `POST /api/directory/verify-upload` (multipart file upload; returns mapping preview or completed verification job)
- `GET /api/directory/verify-jobs`
- `GET /api/directory/verify-jobs/{id}`
- `GET /api/directory/verify-jobs/{id}/rows`
- `GET /api/directory/verify-jobs/{id}/export?file_format=csv|xlsx`

### Directory issues/rules/jobs/provisioning/audit
- `GET /api/directory/issues` (supports `status`, `severity`, `issue_type`, `suggested_action`, `q`)
- `POST /api/directory/issues/scan`
- `POST /api/directory/issues/{id}/approve|reject|mark-exception`
- `POST /api/directory/issues/bulk-approve`
- `GET|POST /api/org-units/templates`
- `PATCH /api/org-units/templates/{id}`
- `GET|POST /api/email-templates`
- `PATCH /api/email-templates/{id}`
- `POST /api/directory/change-jobs/preview`
- `POST /api/directory/change-jobs/execute`
- `GET /api/directory/change-jobs`
- `GET /api/directory/change-jobs/{id}`
- `GET|POST /api/directory/approvals`
- `GET /api/directory/approvals/{id}`
- `POST /api/directory/approvals/{id}/approve|reject|cancel`
- `POST /api/provisioning/preview|create|bulk-preview|bulk-create`
- `GET /api/provisioning/records`
- `GET /api/provisioning/records/{id}`
- `GET /api/directory/audit-logs`
- `GET /api/directory/audit-logs/{id}`

### Classroom operations (implemented)
- `GET /api/classroom/courses`
- `GET /api/classroom/courses/{course_id}/roster`
- `POST /api/classroom/add-student`
- `POST /api/classroom/add-teacher`
- `POST /api/classroom/remove-student`
- `POST /api/classroom/remove-teacher`
- `POST /api/classroom/preflight`
- `POST /api/classroom/courses/create`
- `POST /api/classroom/courses/{course_id}/archive`
- `DELETE /api/classroom/courses/{course_id}`

## Notes
- Directory verification uses locally synced directory data; it does not call Google per uploaded row.
- `directory/stats` and `directory/sync-jobs` are the authoritative sources for sync progress and totals.
- Google write operations remain backend/worker only.
