# 01: Walking skeleton: Compose, pinned stack, PostgreSQL-only tests

**What to build:** A reviewer can clone the repo, copy `.env.example` to `.env`, run one Compose command, and get three running services:
- PostgreSQL 17, reachable only inside the Compose network;
- a Django + DRF backend that runs migrations on start;
- a Vite + React frontend that proxies `/api` to the backend.

Both test runners work inside Compose, and the backend tests can only run against PostgreSQL. This is the base every later ticket builds on (spec §1, §7; ADRs 0004, 0007; visuals 1 and 2).

**Blocked by:** None (can start immediately)

**Status:** done

- [ ] The first commit contains only the existing docs (`CLAUDE.md`, `GLOSSARY.md`, `docs/`, `.scratch/`). Every later change goes in small, separate commits.
- [ ] The repo layout follows visual 2: a backend project with a `config` module, a frontend Vite app, and root `compose.yaml`, `.env.example`, `.gitignore`.
- [ ] Pins are exact: `postgres:17`, Python 3.13, Django `5.2.18`, djangorestframework `3.18.3`, the PostgreSQL driver, pytest and pytest-django. Frontend dependencies are locked by a committed `package-lock.json`. `django-cors-headers` is not installed.
- [ ] `docker compose up --build` starts `db` (with a healthcheck and named volume), `backend` (waits for a healthy `db`, runs migrations, serves on `8000`) and `frontend` (Vite on `5173`).
- [ ] Only ports `5173` and `8000` are published. `db` has no published port.
- [ ] A request to `http://localhost:5173/api/...` reaches Django through the Vite proxy.
- [ ] Settings come from environment variables: `DJANGO_SECRET_KEY`, `DJANGO_DEBUG` (default off), `DJANGO_ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`, the `POSTGRES_*` variables and `DEMO_USER_PASSWORD`. `USE_TZ=True` and `TIME_ZONE="Asia/Qatar"`.
- [ ] With `DEBUG` off, a missing secret key fails startup, and secure cookies, HSTS, nosniff and frame denial are on.
- [ ] No CORS settings or middleware exist.
- [ ] `.env.example` holds only values clearly marked as local demo values. `.env` is git-ignored.
- [ ] `docker compose run --rm backend pytest` runs a placeholder test, and the test settings stop with a clear error if the database engine isn't PostgreSQL.
- [ ] `docker compose run --rm frontend npm test` runs Vitest with a placeholder test.
