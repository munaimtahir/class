# TESTS.md

## Unit tests
- session draft validation
- CSV parser correctness
- duplicate hash/idempotency key generation
- Google API payload builder functions
- publish status transitions

## Integration tests
- auth status endpoint
- create session drafts
- import CSV -> session drafts
- preview publish plan
- queue publish job
- execute mocked Calendar + Classroom publish flow
- retry failed item

## UI tests
- login screen renders
- course list loads
- import page accepts CSV
- review page edits session
- publish planner submits job
- posting log displays statuses

## Acceptance tests
1. Import Tuesday timetable with 4 sessions.
2. Review and edit one title.
3. Publish 2 immediately and schedule 2.
4. Confirm Calendar/Meet records created where needed.
5. Confirm Classroom posts created.
6. Re-import same file and verify duplicates are prevented.
