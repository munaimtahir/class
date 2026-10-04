# Complete Audit Report: CLASS Project

**Generated:** $(date)
**Location:** /home/munaim/srv/apps/class

---

## 1. BACKEND API ENDPOINTS (Django REST Framework)

### Base URL: `/api/`

### A. Authentication Endpoints
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/auth/google/start` | `google_auth_start` | AllowAny |
| GET | `/auth/google/callback` | `google_auth_callback` | AllowAny |
| GET | `/auth/status` | `auth_status` | AllowAny |
| POST | `/auth/logout` | `auth_logout` | Authenticated |

### B. Classroom & Session Management (ViewSets)
**CourseViewSet:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/classrooms/` | list() | Authenticated |
| GET | `/classrooms/{id}/` | retrieve() | Authenticated |
| POST | `/classrooms/sync/` | sync() | Authenticated |

**SessionViewSet:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/sessions/` | list() | Authenticated |
| POST | `/sessions/` | create() | Authenticated |
| GET | `/sessions/{id}/` | retrieve() | Authenticated |
| PATCH | `/sessions/{id}/` | update() | Authenticated |
| DELETE | `/sessions/{id}/` | destroy() | Authenticated |
| POST | `/sessions/generate-meet/` | generate_meet() | Authenticated |
| POST | `/sessions/schedule-posts/` | schedule_posts() | Authenticated |
| POST | `/sessions/publish-now/` | publish_now() | Authenticated |

**LogViewSet:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/logs/` | list() | Authenticated |
| GET | `/logs/{id}/` | retrieve() | Authenticated |

### C. Import Endpoints (Google Sheets & File Upload)
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/imports/google-sheet/preview` | `import_google_sheet_preview` | Authenticated |
| POST | `/imports/file/preview` | `import_file_preview` | Authenticated |
| POST | `/imports/google-sheet/commit` | `import_google_sheet_commit` | Authenticated |
| GET | `/imports/` | `list_import_batches` | Authenticated |
| GET | `/imports/{batch_id}/` | `get_import_batch` | Authenticated |
| POST | `/imports/{batch_id}/promote/` | `promote_import_batch` | Authenticated |

### D. Publish Endpoints (Combined-Day Messages)
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/publish/combined-day-preview` | `combined_day_preview` | Authenticated |
| POST | `/publish/combined-day-post` | `combined_day_publish` | Authenticated |

### E. Admin Endpoints (Phase 2 - Groups, Bundles, Commands)

**Groups:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/groups` | `list_groups` | IsAdminUser |
| POST | `/groups/sync` | `sync_groups` | IsAdminUser |
| POST | `/groups/add-member` | `add_member_to_group` | IsAdminUser |
| POST | `/groups/remove-member` | `remove_member_from_group` | IsAdminUser |
| GET | `/groups/{group_email}/members` | `list_group_members` | IsAdminUser |

**Classroom Admin:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/classroom/courses` | `list_classroom_courses` | IsAdminUser |
| POST | `/classroom/add-student` | `add_student_to_course` | IsAdminUser |
| POST | `/classroom/add-teacher` | `add_teacher_to_course` | IsAdminUser |

**Bundles:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| GET | `/bundles` | `list_bundles` | IsAdminUser |
| POST | `/bundles/create` | `create_bundle` | IsAdminUser |
| PATCH | `/bundles/{bundle_id}` | `update_bundle` | IsAdminUser |
| DELETE | `/bundles/{bundle_id}/delete` | `delete_bundle` | IsAdminUser |

**Commands & Jobs:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/commands/preview` | `commands_preview` | IsAdminUser |
| POST | `/commands/run` | `commands_run` | IsAdminUser |
| GET | `/commands/jobs` | `list_jobs` | IsAdminUser |
| GET | `/commands/jobs/{job_id}` | `get_job` | IsAdminUser |
| GET | `/commands/logs` | `list_command_logs` | IsAdminUser |
| POST | `/commands/retry` | `retry_job` | IsAdminUser |

**CSV Import:**
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/commands/import/csv/preview` | `csv_import_preview` | IsAdminUser |
| POST | `/commands/import/csv/run` | `csv_import_run` | IsAdminUser |

### F. Phase 2B - Classroom Lifecycle (Direct Course Management)
| Method | Path | Handler | Auth |
|--------|------|---------|------|
| POST | `/classroom/preflight` | `classroom_preflight` | IsAdminUser |
| POST | `/classroom/courses/create` | `create_course_view` | IsAdminUser |
| POST | `/classroom/courses/{course_id}/archive` | `archive_course_view` | IsAdminUser |
| DELETE | `/classroom/courses/{course_id}` | `delete_course_view` | IsAdminUser |
| POST | `/classroom/remove-student` | `remove_student_view` | IsAdminUser |
| POST | `/classroom/remove-teacher` | `remove_teacher_view` | IsAdminUser |

### Command Types Supported (via `/commands/preview` and `/commands/run`)
- `ADD_USER_TO_GROUP`
- `REMOVE_USER_FROM_GROUP`
- `ADD_STUDENT_TO_COURSE`
- `ADD_TEACHER_TO_COURSE`
- `ENROLL_GROUP_TO_COURSE`
- `APPLY_ONBOARDING_BUNDLE`
- `CSV_IMPORT`

---

## 2. FRONTEND ROUTES (Next.js App Router)

### Public Routes (No Auth Check)
| Route | File | Purpose |
|-------|------|---------|
| `/` | `apps/web/app/page.tsx` | Dashboard / Login Gate |
| `/imports` | `apps/web/app/imports/page.tsx` | Google Sheet & File Import |
| `/publish` | `apps/web/app/publish/page.tsx` | Combined-Day Post Timetable |

### Admin Routes
| Route | File | Purpose |
|-------|------|---------|
| `/admin` | `apps/web/app/admin/page.tsx` | Admin Index |
| `/admin/groups` | `apps/web/app/admin/groups/page.tsx` | Google Groups Management |
| `/admin/courses` | `apps/web/app/admin/courses/page.tsx` | Classroom Course Management |
| `/admin/bundles` | `apps/web/app/admin/bundles/page.tsx` | Onboarding Bundles |
| `/admin/commands` | `apps/web/app/admin/commands/page.tsx` | Command Runner |
| `/admin/jobs` | `apps/web/app/admin/jobs/page.tsx` | Jobs & Logs History |

### Layout Structure
- **Root Layout:** `apps/web/app/layout.tsx` (basic HTML structure, no special auth handling)
- **Admin Layout:** `apps/web/app/admin/layout.tsx` (navigation bar with sidebar links)

**IMPORTANT NOTE:** No auth middleware or automatic route protection in Next.js layer. Auth checks happen at component level via `api.authStatus()` call on component mount.

---

## 3. AUTHENTICATION FLOW

### Login Sequence
1. User visits `/`
2. `page.tsx` calls `api.authStatus()` on mount via `useEffect`
3. If `authenticated=false`, shows "Login with Google" button
4. User clicks → `api.authStart()` → returns `auth_url` (Google OAuth URL)
5. User redirected to Google OAuth consent screen
6. Google callback: `GET /api/auth/google/callback?code=...`
7. Backend exchanges code for `access_token` via Google OAuth API
8. Backend creates/updates User in DB with:
   - `google_id`
   - `access_token`
   - `refresh_token` (stored encrypted via Fernet)
9. Backend calls `django.contrib.auth.login()` to set session cookie
10. Redirects to `FRONTEND_URL` (from env)
11. Frontend reloads, calls `api.authStatus()` again → `authenticated=true`, returns user data

### Session/Token Storage
- **Method:** HTTP-only session cookies (Django's default, NOT JWT)
- **NOT using:** localStorage or sessionStorage
- **Transport:** Cookie-based auth with `credentials: include` in fetch calls (`lib/api.ts`)
- **Automatic:** All API calls automatically send session cookie

### Logout Flow
- `POST /api/auth/logout` → calls `django.contrib.auth.logout()`
- Clears session cookie
- Backend: `/auth/logout` handler in `views.py`

### Component-Level Auth Checks
In `page.tsx` and other protected pages:
- Calls `api.authStatus()` on component mount
- Checks `auth.authenticated` boolean
- If false, renders login gate
- If true, renders dashboard/content

### Admin Authentication (Phase 2)
- **Backend:** `@permission_classes([IsAdminUser])` decorator on admin views
- **Check:** Custom permission class validates `user.is_admin` flag
- **Frontend:** NO explicit auth check on admin routes
  - Routes are technically accessible, but API calls fail if user not admin
  - User sees error messages from API responses (error handling in components)

### NO MIDDLEWARE IN NEXT.JS
Auth is purely handled at:
- **API level:** Django REST Framework permission classes
- **Component level:** Conditional rendering based on `api.authStatus()` response

---

## 4. lib/api.ts - COMPLETE API OBJECT

### Source File
`apps/web/lib/api.ts` (186 lines)

### EXPORT 1: `api` (Main API Methods)

**Authentication & Session:**
```typescript
api.authStatus()          // GET /auth/status
api.authStart()           // GET /auth/google/start
```

**Courses/Classrooms:**
```typescript
api.courses()             // GET /classrooms/
api.syncCourses()         // GET /classrooms/sync/
```

**Sessions:**
```typescript
api.sessions()                          // GET /sessions/
api.createSession(payload)              // POST /sessions/
api.updateSession(id, payload)          // PATCH /sessions/{id}/
api.deleteSession(id)                   // DELETE /sessions/{id}/
api.generateMeet(session_ids)           // POST /sessions/generate-meet/
api.schedulePosts(session_ids)          // POST /sessions/schedule-posts/
api.publishNow(session_ids)             // POST /sessions/publish-now/
```

**Logs:**
```typescript
api.logs()                              // GET /logs/
```

**Google Sheet Import:**
```typescript
api.previewSheetImport(payload)         // POST /imports/google-sheet/preview
api.commitSheetImport(payload)          // POST /imports/google-sheet/commit
api.listImportBatches()                 // GET /imports/
api.getImportBatch(id)                  // GET /imports/{id}/
api.promoteImportBatch(id)              // POST /imports/{id}/promote/
```

**File Import:**
```typescript
api.previewFileImport(file, fields)     // POST /imports/file/preview (multipart/form-data)
```

**Combined-Day Publishing:**
```typescript
api.combinedDayPreview(payload)         // POST /publish/combined-day-preview
api.combinedDayPublish(payload)         // POST /publish/combined-day-post
```

**Groups (Phase 2):**
```typescript
api.listGroups()                        // GET /groups
api.syncGroups(domain?)                 // POST /groups/sync
api.addMemberToGroup(group_email, user_email)  // POST /groups/add-member
api.removeMemberFromGroup(group_email, user_email) // POST /groups/remove-member
api.groupMembers(group_email)           // GET /groups/{group_email}/members
```

**Classroom Admin (Phase 2):**
```typescript
api.adminCourses()                      // GET /classroom/courses
api.addStudent(course_id, student_email) // POST /classroom/add-student
api.addTeacher(course_id, teacher_email) // POST /classroom/add-teacher
```

**Bundles (Phase 2):**
```typescript
api.listBundles(active_only?)           // GET /bundles?active_only=true
api.createBundle(payload)               // POST /bundles/create
api.updateBundle(id, payload)           // PATCH /bundles/{id}
api.deleteBundle(id)                    // DELETE /bundles/{id}/delete
```

**Commands (Phase 2):**
```typescript
api.commandPreview(command_type, params)  // POST /commands/preview
api.commandRun(command_type, params, dry_run?) // POST /commands/run
api.listJobs()                          // GET /commands/jobs
api.getJob(id)                          // GET /commands/jobs/{id}
api.commandLogs()                       // GET /commands/logs
api.retryJob(job_id)                    // POST /commands/retry
```

**CSV Import (Phase 2):**
```typescript
api.csvPreview(csv_text, default_bundle_id?)  // POST /commands/import/csv/preview
api.csvRun(csv_text, default_bundle_id?, dry_run?) // POST /commands/import/csv/run
```

### EXPORT 2: `phase2bApi` (Phase 2B Lifecycle Management)

**Classroom Lifecycle:**
```typescript
phase2bApi.classroomPreflight(action, params)  // POST /classroom/preflight
phase2bApi.createCourse(data)                  // POST /classroom/courses/create
phase2bApi.archiveCourse(course_id)            // POST /classroom/courses/{course_id}/archive
phase2bApi.deleteCourse(course_id)             // DELETE /classroom/courses/{course_id}
phase2bApi.removeStudent(course_id, student_email)  // POST /classroom/remove-student
phase2bApi.removeTeacher(course_id, teacher_email)  // POST /classroom/remove-teacher
```

### Internal Helper Functions

```typescript
async function req(path: string, init: RequestInit = {})
  // Base fetch wrapper
  // - Adds credentials: "include" (sends cookies)
  // - Sets Content-Type: application/json
  // - Adds cache: "no-store"
  // - Returns JSON response or null for 204 No Content

async function reqForm(path: string, body: FormData, init: RequestInit = {})
  // FormData wrapper (for file uploads)
  // - Sets credentials: "include"
  // - Sets cache: "no-store"
  // - Does NOT set Content-Type (browser handles multipart boundary)

function resolveApiBase()
  // Resolves API base URL from environment
  // 1. Reads process.env.NEXT_PUBLIC_API_URL
  // 2. If empty or "/", returns "/api"
  // 3. If matches localhost/127.0.0.1, returns "/api"
  // 4. Otherwise, returns full URL (trailing slash removed)

const API_URL: string
  // Resolved base URL, used by req() and reqForm()
```

---

## 5. PLAYWRIGHT E2E TESTS

### Location
`apps/web/tests/e2e/`

### Files
- **`dashboard.spec.ts`** - Main test suite (142 lines, 8 test cases)
- **`mock-api.ts`** - MockApi class for intercepting API calls

### Test Cases
1. "shows the login gate and starts OAuth"
2. "syncs classrooms and filters sessions by selected course"
3. "creates a session from the session manager form"
4. "edits and deletes an existing session"
5. "generates meet links and surfaces them in the table and logs"
6. "schedules selected posts and updates status to scheduled"
7. "publishes immediately and ensures meet-required sessions end with a meet link"
8. "shows not required for sessions that do not need a meet link"

### Mock API Features (mock-api.ts)
- Intercepts API calls via Playwright's route interception
- Mocks auth status (authenticated/not authenticated)
- Returns mock session, course, and group data
- Supports session creation, updating, deletion lifecycle
- Mock meet link generation (e.g., `https://meet.google.com/test-{session_id}`)
- Tracks API call counts (e.g., `authStartCalls`)
- Builds default session objects with realistic data

---

## 6. ADMIN LAYOUT

### Location
`apps/web/app/admin/layout.tsx` (42 lines)

### Visual Structure
- **Header:** Dark (#1a1a2e) navigation bar with white text
- **Styling:** Minimal, functional inline styles
- **Max Content Width:** 1100px

### Navigation Items
```
🛠 Admin
├── /admin/groups       → Groups
├── /admin/courses      → Courses
├── /admin/bundles      → Bundles
├── /admin/commands     → Command Runner
├── /admin/jobs         → Jobs & Logs
└── [spacer] ← Back to app (right-aligned)
```

### Active Link Highlighting
- **Active link color:** #7bc8f6 (light blue)
- **Active link weight:** 700 (bold)
- **Inactive link color:** #ccc
- **Inactive link weight:** 400

---

## 7. MIDDLEWARE

### Status: NO middleware.ts EXISTS

The project has NO `middleware.ts` file in `apps/web/`.

### Why No Middleware?
Authentication is handled purely at:

1. **API Level:**
   - Django REST Framework permission classes
   - `@permission_classes([IsAdminUser])` decorators
   - Session-based auth via HTTP-only cookies

2. **Component Level:**
   - Components call `api.authStatus()` on mount
   - Conditional rendering based on response
   - Error handling for unauthorized API responses

### Result
- Routes are publicly accessible in Next.js
- Auth enforcement happens at backend API
- Frontend pages gracefully handle auth failures

---

## 8. DOMAIN & BASE URL STRUCTURE

### Infrastructure (from .env.example)

**Public Domain:**
```
APP_DOMAIN=class.alshifalab.pk
FRONTEND_URL=https://class.alshifalab.pk
```

**Local Binding:**
```
FRONTEND_BIND_HOST=127.0.0.1
FRONTEND_BIND_PORT=9030
BACKEND_BIND_HOST=127.0.0.1
BACKEND_BIND_PORT=9031
```

**Routing:**
- Expected to be proxied via **Caddy** (Docker orchestration)
- Caddy routes requests to frontend (port 9030) and backend (port 9031)
- All served under single domain: `class.alshifalab.pk`

### OAuth Configuration

**Google Redirect URI:**
```
GOOGLE_REDIRECT_URI=https://class.alshifalab.pk/api/auth/google/callback
```

### API Base URL Resolution (lib/api.ts)

**next.config.js:** Minimal config (no custom basePath)

**Runtime Resolution (resolveApiBase()):**
1. Check `NEXT_PUBLIC_API_URL` environment variable
2. If empty or `/`, use `/api` (relative path to same domain)
3. If matches `localhost` or `127.0.0.1`, use `/api`
4. Otherwise, use full URL provided
5. All trailing slashes removed

**Result:** API calls go to `/api/` by default

### CORS & CSRF Configuration

**CORS:**
```
CORS_ALLOWED_ORIGINS=https://class.alshifalab.pk
```

**CSRF:**
```
CSRF_TRUSTED_ORIGINS=https://class.alshifalab.pk
```

### Database & Cache

**PostgreSQL:**
```
POSTGRES_DB=classdb
POSTGRES_USER=classuser
POSTGRES_PASSWORD=classpass
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

**Redis (Celery):**
```
CELERY_BROKER_URL=redis://redis:6379/0      (broker)
CELERY_RESULT_BACKEND=redis://redis:6379/1  (results)
```

---

## SUMMARY STATISTICS

### Backend API
- **Total endpoints:** ~50+ (including ViewSet CRUD actions)
- **Protected (IsAdminUser):** ~30+
- **Authenticated:** ~15
- **Public:** ~4

### Frontend Pages
- **Total routes:** 9
- **Admin routes:** 6
- **Public routes:** 3
- **Layouts:** 2 (root + admin)

### Test Coverage
- **E2E test cases:** 8
- **Mock API support:** Yes (with route interception)

### Authentication
- **Method:** OAuth 2.0 (Google)
- **Session:** HTTP-only cookies (no JWT)
- **Admin:** Role-based (user.is_admin flag)
- **Protection:** API-level + component-level

### Storage
- **Database:** PostgreSQL
- **Cache/Queue:** Redis (Celery)
- **Secret Key:** Fernet (for refresh token encryption)

---

## FILE LOCATIONS (AUDIT REFERENCE)

### Backend Files
- `/home/munaim/srv/apps/class/apps/api/core/urls.py` - Route definitions
- `/home/munaim/srv/apps/class/apps/api/core/views.py` - Main view handlers
- `/home/munaim/srv/apps/class/apps/api/core/admin_views.py` - Admin view handlers
- `/home/munaim/srv/apps/class/apps/api/config/urls.py` - Main Django URL config

### Frontend Files
- `/home/munaim/srv/apps/class/apps/web/app/page.tsx` - Home/Dashboard
- `/home/munaim/srv/apps/class/apps/web/app/layout.tsx` - Root layout
- `/home/munaim/srv/apps/class/apps/web/app/imports/page.tsx` - Import page
- `/home/munaim/srv/apps/class/apps/web/app/publish/page.tsx` - Publish page
- `/home/munaim/srv/apps/class/apps/web/app/admin/layout.tsx` - Admin layout
- `/home/munaim/srv/apps/class/apps/web/app/admin/page.tsx` - Admin index
- `/home/munaim/srv/apps/class/apps/web/app/admin/groups/page.tsx` - Groups management
- `/home/munaim/srv/apps/class/apps/web/app/admin/courses/page.tsx` - Courses management
- `/home/munaim/srv/apps/class/apps/web/app/admin/bundles/page.tsx` - Bundles management
- `/home/munaim/srv/apps/class/apps/web/app/admin/commands/page.tsx` - Command runner
- `/home/munaim/srv/apps/class/apps/web/app/admin/jobs/page.tsx` - Jobs & logs

### API Layer
- `/home/munaim/srv/apps/class/apps/web/lib/api.ts` - All API methods
- `/home/munaim/srv/apps/class/apps/web/next.config.js` - Next.js config

### Tests
- `/home/munaim/srv/apps/class/apps/web/tests/e2e/dashboard.spec.ts` - E2E tests
- `/home/munaim/srv/apps/class/apps/web/tests/e2e/mock-api.ts` - Mock API helper

### Configuration
- `/home/munaim/srv/apps/class/.env.example` - Environment variables template

---

**END OF AUDIT REPORT**
