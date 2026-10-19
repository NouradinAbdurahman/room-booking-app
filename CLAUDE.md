# Room Booking App: orientation

A meeting-room booking app for an office in Doha. Logged-in Users see Rooms and a Room's bookings for a Day, book a Room, and cancel their own bookings. **The database itself prevents double-booking**, including under simultaneous requests.

Stack: Django 5.2 + DRF on PostgreSQL 17 (`backend/`), React 19 + Vite (`frontend/`), all in Docker Compose. **All 14 tickets are done**; read [`README.md`](README.md) for the full picture.

## Where things are

| What | Where |
| --- | --- |
| Vocabulary (Booking, Booker, Day, Slot…) | [`GLOSSARY.md`](GLOSSARY.md) |
| Decisions and why (read before changing an area) | [`docs/adr/`](docs/adr/) 0001–0007 |
| Spec, completed tickets, evidence | [`.scratch/room-booking-app/`](.scratch/room-booking-app/): `spec.md`, `issues/` (01–14, done), `evidence/` (constraints, security checklist, query plans) |
| Booking rules (validation order, `409` mapping, deadlock retry, cancel) | `backend/bookings/services.py` |
| Database constraints and indexes | `backend/bookings/models.py`, `backend/rooms/models.py` |
| List queries (Day schedule, My Bookings) | `backend/bookings/queries.py` |
| Auth, CSRF and the error envelope | `backend/accounts/`, `backend/config/exceptions.py` |
| Backend tests | `backend/tests/` |
| Doha time (frontend) | `frontend/src/utils/dohaTime.js` |
| All HTTP and CSRF (frontend) | `frontend/src/api/client.js` |

## Commands

```sh
cp .env.example .env && docker compose up --build       # app at http://localhost:5173 (demo users user1-3)
docker compose run --rm backend pytest                   # backend tests, PostgreSQL only
docker compose run --rm frontend npm test                # frontend tests (TZ=America/New_York)
docker compose run --rm backend python manage.py makemigrations --check --dry-run
docker compose run --rm frontend npx vite build --outDir /tmp/build
```

## Non-negotiable rules

- **Backend tests run on PostgreSQL only.** Never switch to SQLite, and never weaken, skip or delete a test to make a change pass.
- **Never weaken or bypass the double-booking protection.** That is the `no_overlapping_active_bookings` exclusion constraint and the CHECK constraints (ADRs 0001–0003). Only SQLSTATE `23P01` from that named constraint maps to `409`.
- **Preserve Doha time:** store UTC, require offsets, speak `Asia/Qatar`, and a Day means overlap (ADR 0005).
- **Preserve auth, CSRF and cancellation:** session auth with explicit CSRF, including on login; `401` when logged out; the User always comes from the session; only the Booker cancels (ADRs 0002, 0004).
- **No secrets in the repository.** `.env` stays untracked, and `.env.example` holds only marked demo values.
- **No destructive or global Docker commands** (`docker volume prune`, `docker system prune`, `down -v` on this project). Never wipe or reseed the development database's existing data.

## How to make a change

1. **Before touching anything,** inspect `git status`, `git log` and the working tree. Preserve any existing user changes. Do not redo completed tickets.
2. **Read** the ADRs and spec sections for the area, and the existing tests for it.
3. **Make one focused change,** adding or updating tests (test-first where practical).
4. **Run the relevant checks** above. Run the full suites before committing.
5. **Review the diff** for unintended changes, then commit in small, clear commits. If a change contradicts an ADR, say so and ask; do not silently override it.

## Agent skills

### Issue tracker

Issues live as local markdown files under `.scratch/<feature>/`. See `docs/agents/issue-tracker.md`.

### Triage labels

Default vocabulary: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: one root `GLOSSARY.md` plus `docs/adr/`. See `docs/agents/domain.md`.
