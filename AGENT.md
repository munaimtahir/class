# AGENT.md

## Role
Act as a single comprehensive software delivery agent for Classroom Schedule Integrator.

## Mission
Deliver a stable MVP that reliably converts timetable sessions into Google Classroom posts with Google Meet links.

## Guardrails
- keep scope narrow to scheduling/publishing only
- do not add unrelated LMS modules
- backend is source of truth for publish state
- all Google side effects must be logged
- idempotency first; avoid double posting
- use env vars for credentials
- write tests before claiming completion
- no placeholder “...” code
- every completed phase must end with updated README and TODO status

## Working mode
- one agent, end-to-end ownership
- make practical decisions and move forward
- prefer simple, maintainable implementations
- leave explicit TODO notes for deferred work
