# DATAMODEL.md

## Entities

### User
- id
- email
- full_name
- role
- created_at

### WorkspaceConnection
- id
- user_id
- provider
- google_subject_id
- scopes_json
- token_meta_json
- connected_at
- last_refresh_at

### CourseMap
- id
- user_id
- google_course_id
- course_name
- section
- room
- owner_email
- active
- synced_at

### ImportBatch
- id
- user_id
- source_type (csv/manual/google_sheet)
- source_ref
- imported_at
- row_count
- status

### SessionDraft
- id
- import_batch_id
- course_map_id
- date
- start_time
- end_time
- title
- subject
- topic
- subgroup_label
- requires_meet
- publish_mode (now/scheduled)
- scheduled_for
- topic_label
- notes
- dedupe_hash
- status
- validation_errors_json

### PublishJob
- id
- created_by
- scope_type (single/day/week/batch)
- scheduled_for
- status
- result_summary_json
- created_at

### CalendarEventRecord
- id
- session_draft_id
- google_event_id
- meet_url
- html_link
- status
- created_at

### ClassroomPostRecord
- id
- session_draft_id
- google_course_id
- google_post_id
- post_type
- alternate_link
- status
- created_at

### AuditLog
- id
- actor_id
- action
- entity_type
- entity_id
- details_json
- created_at
