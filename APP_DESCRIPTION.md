# Plain-Language App Description

## App name
Classroom Schedule Integrator

## What problem it solves
Academic staff often prepare weekly teaching timetables in Word, Excel, or Google Sheets, but then still have to manually create Google Classroom posts and Google Meet links. This causes duplication, missed sessions, wrong links, formatting inconsistency, and wasted time.

This app turns timetable data into scheduled Google Classroom-ready session posts.

## Main user
A timetable/admin user in a medical college or school who manages class schedules and publishes sessions into Google Classroom.

## Core workflow
1. User signs in with approved Google Workspace account.
2. User selects the target Google Classroom course.
3. User imports session data from Google Sheet, CSV, or manual entry.
4. App converts rows into structured sessions.
5. User reviews and edits sessions before publishing.
6. App creates Calendar events with Google Meet links where required.
7. App creates Classroom posts linked to those Meet sessions.
8. App schedules posts or publishes immediately.
9. App stores a posting log and shows success/failure status.

## First version scope
### Include
- Google sign-in
- fetch accessible Google Classroom courses
- basic timetable/session import
- session preview and edit screen
- Meet generation through Calendar events
- Classroom post creation
- scheduled publishing
- posting history and status log
- duplicate prevention

### Exclude for now
- attendance
- grading
- student analytics
- OCR timetable reading from images
- full LMS replacement
- parent/student portals
- faculty reminders
- advanced subgroup permissions

## Main screens
1. Login / Connect Google
2. Course Selector
3. Timetable Import
4. Session Review
5. Publish Planner
6. Posting Log

## Session model in simple words
Each session should have:
- date
- start time
- end time
- title
- subject
- topic/description
- target course
- subgroup or audience label
- needs Meet or not
- publish mode (now or scheduled)
- publish status

## Real example
Tuesday 10 March 2026:
- 9:40–10:30 Physiology Lec-12 — Autonomic Nervous System I
- 10:30–11:20 Embryology Lec-4 — Development of Skull

The app should let the user review these items, generate Meet links, and publish them as Classroom materials under the correct topic.

## Why this should be built first
It solves a repeated operational task immediately and can later grow into timetable automation, reminders, and broader academic workflow tools.
