# App Description

## Product definition
`class` is a narrow institutional operations platform for Google Workspace/Classroom workflows.

It combines:
- an implemented MVP publishing core
- an official post-MVP expansion scope: **Stage 3A — User Operations and Resolution** via the **User Resolution Center**

The product is for institutional operators and academic operations teams. It is not a generic LMS and not a general IT helpdesk.

## MVP publishing workflow (implemented)
1. Operator signs in with Google Workspace.
2. Operator syncs accessible Classroom courses.
3. Operator creates sessions manually or imports from Google Sheets.
4. Operator reviews draft rows, then promotes accepted rows.
5. Operator generates Meet links when required.
6. Operator publishes now, schedules posts, or publishes combined-day announcements.
7. Operator monitors outcomes in posting logs.

## Stage 3A module: User Resolution Center (official expansion scope)
The User Resolution Center provides bounded operational issue handling for users blocked in the platform workflow.

### Who uses it
- Operations operators handling day-to-day timetable/publish incidents
- Academic support or program coordinators tracking unresolved user blockers
- Admin reviewers for escalated cases requiring higher-level intervention

### Problems it solves
- Captures and tracks user issues tied to Google Workspace/Classroom operational readiness
- Connects each issue to affected user/course/session/publish context
- Supports diagnosis, assignment, collaboration, escalation, and resolution tracking
- Preserves an auditable operator trail for every issue action

### In-scope issue categories
- Official institutional email readiness/access issues
- Missing or wrong Classroom enrollment
- Faculty permission/access issues affecting operations
- Timetable/session mapping mismatches
- Missing Meet links
- Session publish failures and retry outcomes
- Wrong/duplicate account mapping that affects course/session/material access

### Out-of-scope issue categories
- Hardware/network/device support
- Generic IT complaints unrelated to app workflows
- LMS-gradebook/attendance/exam concerns
- Broad ERP or non-Classroom institutional operations

## How Stage 3A connects to existing product data
- Issues link to existing `User`, `Course`, `Session`, `MeetEvent`, `ClassroomPost`, and `PostLog` context.
- Resolution actions can trigger existing operational workflows (for example, re-run publish or regenerate Meet) through backend/worker paths.
- Action history and outcomes are captured for traceability and dashboard reporting.

## Core product principles
- Preserve MVP publishing reliability while extending operational support capability.
- Keep Google write operations in backend/worker only.
- Maintain clear boundaries between in-scope operational resolution and out-of-scope helpdesk requests.
- Ensure every high-impact workflow step is visible, traceable, and reviewable.
