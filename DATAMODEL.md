# Data Model

## Ownership model
- Google Workspace/Classroom are source of truth for real account/classroom state.
- Local DB stores operational cache, workflow state, and audit history.

## MVP core entities (implemented)
- `User`: auth identity + OAuth token metadata
- `Course`: mapped Google Classroom course
- `Session`: timetable session and publish state
- `MeetEvent`: generated Calendar event + Meet URL
- `ClassroomPost`: publish/schedule record
- `PostLog`: publish lifecycle logs
- `ImportBatch`, `SessionDraft`: import preview/commit/promote lifecycle

## Directory entities (implemented)

### `DirectoryUser`
- Google user cache (`google_user_id`, `primary_email`, name, OU, suspended/archived)
- operational identifiers (`external_identifier`, `roll_number`, `employee_id`)
- normalized fields (`normalized_email`, `normalized_full_name`, `normalized_phone`)
- contact aliases (`aliases_json`, `phones_json`)
- sync metadata (`last_synced_at`, `last_seen_at`, `sync_source`, `is_active`)

### `DirectorySyncJob`
- sync lifecycle: `queued|running|completed|failed`
- sync scope: `query`, optional `max_results`
- counters: `pages_fetched`, `users_fetched_total`, `users_upserted_total`, `users_created_total`, `users_updated_total`
- result/error payloads and timestamps

### `DirectoryVerifyJob`
- upload source metadata (`source_filename`, `source_type`, optional `sheet_name`)
- lifecycle: `uploaded|processing|completed|failed`
- verification summary totals and persisted column mapping

### `DirectoryVerifyRow`
- row-level input payload and row number
- matched user fields (`matched_directory_user`, `matched_email`, `matched_name`)
- match metadata (`match_basis`, `confidence_score`, `notes`)
- verdict: `exists|does_not_exist|ambiguous|invalid_input`

## Existing directory governance entities
- `DirectoryIssue`
- `OrgUnitTemplate`
- `EmailTemplateRule`
- `DirectoryChangeJob` / `DirectoryChangeJobItem`
- `ProvisioningRecord`
- `ApprovalRequest`
- `DirectoryAuditLog`
