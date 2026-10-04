# Tasks

## MVP core (implemented)
- [x] OAuth, course sync, session CRUD
- [x] import preview/commit/promote
- [x] Meet generation
- [x] publish now/schedule
- [x] posting logs
- [x] production admin static asset serving for `/django-admin/`

## Directory foundation and verification (implemented)
- [x] Google Directory sync cache (`DirectoryUser`)
- [x] paginated sync with cumulative counters (not first-page totals)
- [x] sync job tracking (`DirectorySyncJob`)
- [x] authoritative stats endpoint (`/api/directory/stats`)
- [x] CSV/XLSX upload analysis + column mapping flow
- [x] local-index verification engine with verdicts
- [x] verification job/row persistence (`DirectoryVerifyJob`, `DirectoryVerifyRow`)
- [x] verification rows listing with filtering/pagination
- [x] CSV/XLSX export endpoints
- [x] verification dashboard page and navigation wiring

## Remaining hardening
- [ ] add background execution option for very large verification uploads
- [ ] add retention policy and cleanup job for old verification artifacts
- [ ] add server-side cursor pagination for very large directory user lists

## Auth and scope hardening (implemented)
- [x] canonical Google scope registry with feature map
- [x] preflight scope validation before protected Google operations
- [x] structured missing-scope API responses with reconnect hint
- [x] auth start modes for reconnect and feature upgrades
- [x] OAuth callback persistence for normalized scopes and token metadata
- [x] frontend scope-missing UX prompt with reconnect action
