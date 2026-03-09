# API / Interfaces

## Auth
- `GET /api/auth/google/start`
- `GET /api/auth/google/callback`
- `GET /api/auth/status`
- `POST /api/auth/logout`

## Courses
- `GET /api/courses`
- `POST /api/courses/sync`

## Session drafts
- `GET /api/sessions`
- `POST /api/sessions`
- `GET /api/sessions/{id}`
- `PATCH /api/sessions/{id}`
- `DELETE /api/sessions/{id}`

## Imports
- `POST /api/imports/csv`
- `POST /api/imports/manual`
- `POST /api/imports/google-sheet/preview`

## Publish
- `POST /api/publish/preview`
- `POST /api/publish/jobs`
- `POST /api/publish/jobs/{id}/run`
- `POST /api/publish/jobs/{id}/retry`
- `GET /api/publish/jobs`
- `GET /api/publish/logs`

## Suggested request shape for session draft
```json
{
  "course_map_id": 1,
  "date": "2026-03-10",
  "start_time": "09:40",
  "end_time": "10:30",
  "title": "Physiology Lec-12",
  "subject": "Physiology",
  "topic": "Autonomic Nervous System I",
  "subgroup_label": "Whole class",
  "requires_meet": true,
  "publish_mode": "scheduled",
  "scheduled_for": "2026-03-10T09:30:00+05:00",
  "topic_label": "Week 3 Neurosciences - Tuesday"
}
```
