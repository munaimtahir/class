# QA Checklist

## MVP publishing regression
- [ ] login and Classroom sync still work
- [ ] import preview/commit/promote still works
- [ ] publish now/schedule/combined-day still works
- [ ] publish logs and retry behavior remain intact

## Directory sync correctness
- [ ] sync can process directories larger than 500 users
- [ ] `synced` is cumulative across pages, not first-page count
- [ ] dashboard and stats use authoritative totals from DB/sync-job state
- [ ] running sync shows in-progress cumulative fetched counts
- [ ] completed sync shows final totals and completion timestamp

## Directory verification workflow
- [ ] CSV upload accepted and header analysis returned
- [ ] XLSX upload accepted and sheet selection works
- [ ] column mapping can be adjusted before run
- [ ] results include `exists`, `does_not_exist`, `ambiguous`, `invalid_input`
- [ ] weak multi-candidate name-only rows become `ambiguous` (not false `exists`)
- [ ] insufficient rows become `invalid_input`
- [ ] summary cards match row verdict totals
- [ ] CSV export works
- [ ] XLSX export works

## Scope boundaries
- [ ] feature stays bounded to directory verification (no user creation/password/OU auto-mutation added here)
- [ ] no unrelated LMS/attendance/grading/student-portal scope introduced

## Google permission resilience
- [ ] blocked actions return `GOOGLE_SCOPE_MISSING` (not vague provider errors)
- [ ] response includes `feature`, `missingScopes`, and `reauthorizeUrl`
- [ ] reconnect/upgrade button is visible for blocked actions
- [ ] reconnect flow returns to app and original action can be retried
- [ ] users connected before new scopes can recover via one-time reconnect
