# Setup

## Local prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL 16+
- Redis

## Google configuration
1. Configure a Google Cloud project.
2. Enable Classroom API, Calendar API, Sheets API, and Admin SDK Directory API.
3. Create OAuth credentials.
4. Set redirect URI for `/api/auth/google/callback`.
5. Configure `.env` with Google/app settings.
6. Ensure the OAuth consent screen includes all required operational scopes used by this app.

## Local startup
1. Start backend + worker + frontend (or Docker Compose).
2. Authenticate with an operator/admin Workspace account.
3. Run classroom sync and import preview to validate MVP flow.
4. Run directory sync to populate local `DirectoryUser` cache before verification uploads.

## Directory verification notes
- Supported upload formats: CSV/TSV/TXT/XLSX/XLSM.
- XLSX parsing uses `openpyxl` (already included in backend dependencies).
- No additional environment variables were introduced for this module.

## OAuth reconnect and scope upgrades
- The app validates scopes per feature before calling Google APIs.
- If a user connected before newer scopes were introduced, actions may return `GOOGLE_SCOPE_MISSING`.
- Use:
  - `/api/auth/google/start?mode=reconnect` for full permission refresh
  - `/api/auth/google/start?mode=upgrade&upgrade=<feature>` for targeted scope upgrades
- After callback, the backend updates stored scope metadata (`google_scopes_json`, token metadata, refresh timestamp).
