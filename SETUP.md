# SETUP.md

## Local prerequisites
- Node.js 20+
- Python 3.12+
- PostgreSQL 16+
- Redis

## Local startup outline
1. Configure Google Cloud project.
2. Enable Classroom API, Calendar API, Sheets API.
3. Create OAuth credentials.
4. Set allowed redirect URI.
5. Fill `.env` files.
6. Start backend.
7. Start worker.
8. Start frontend.

## First local checks
- login works
- course sync works
- sample CSV imports
- preview publish plan returns sessions
- mocked publish run succeeds
