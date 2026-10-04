# Tests

## Strategy
Keep MVP publish flows stable while validating directory sync/verification correctness and safety.

## MVP baseline tests
- import parsing/validation/dedupe
- publish orchestration (now/scheduled/combined-day)
- auth/session/log behavior

## Directory sync tests
- paginated sync accumulates totals beyond 500 users
- sync response exposes `pages_fetched`, `synced`, and authoritative `total_directory_users`
- `directory/stats` returns DB-true totals and latest sync job state
- normalized searchable fields are populated during sync upserts

## Directory verification tests
- CSV upload analysis returns mapping metadata
- XLSX upload analysis returns mapping metadata + sheet handling
- verification run creates `DirectoryVerifyJob` + `DirectoryVerifyRow`
- verdict behavior:
  - exact email/official email -> `exists`
  - no match -> `does_not_exist`
  - multiple plausible candidates -> `ambiguous`
  - insufficient input -> `invalid_input`
- exports return CSV/XLSX payloads

## Frontend tests
- directory dashboard shows authoritative stats and sync progress
- verification page supports upload, mapping, results table, and export actions

## Regression rule
- Directory module changes must not break core timetable publishing tests.
