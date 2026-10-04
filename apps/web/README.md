# apps/web
Next.js dashboard for login, session management, publish actions, and logs.

## Playwright E2E

Install frontend dependencies in `apps/web`:

```bash
npm install
```

Run the local Playwright suite:

```bash
npm run test:e2e
```

If the host machine is missing browser system libraries, run the suite in the Playwright container instead:

```bash
docker run --rm -v "$PWD/apps/web:/work" -w /work mcr.microsoft.com/playwright:v1.52.0-noble /bin/bash -lc 'npm run test:e2e'
```
