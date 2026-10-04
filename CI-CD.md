# CI/CD

## Current minimum pipeline
- install backend and frontend dependencies
- lint backend and frontend code
- run backend tests
- run frontend tests
- run type checks
- build deployable artifacts

## Environment separation
- local
- staging
- production

## Required secrets
- Google OAuth client ID
- Google OAuth client secret
- Django secret key
- database URL
- Redis URL
- token encryption key

## Stage 3A CI additions (User Resolution Center)
- API contract tests for issue create/list/detail/update actions
- integration tests for assignment, status transitions, resolve, and escalate flows
- dashboard summary/count correctness checks
- regression checks to ensure MVP publish flows still pass

## Future adjacent CI additions (roadmap)
- Directory Management integration smoke tests when Stage 3B starts
- Enrollment workflow smoke tests when Stage 3C starts
