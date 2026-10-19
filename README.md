# Room Booking

A small meeting-room booking app for an office in Doha. A logged-in User can see the Rooms and a Room's bookings for any Day, book a Room for a time slot, and cancel their own bookings.

The database itself makes a double-booking impossible, including when two people book the same slot at the same moment.

**Stack:** Django 5.2 LTS + Django REST Framework 3.18 · PostgreSQL 17 · React 19 + Vite · Docker Compose.

The words used throughout (Booking, Booker, Slot, Day, Doha time…) are defined in [`GLOSSARY.md`](GLOSSARY.md).

**Contents:**
- [Quick start](#quick-start) (demo logins, tests)
- [Booking rules](#what-it-does-the-booking-rules)
- [Main design decisions](#main-design-decisions)
- [API](#api) and [errors](#errors)
- [Security](#security)
- [Indexes](#database-indexes-and-evidence) and [performance](#performance)
- [Tests and why](#tests-and-why-these-ones)
- [Readings of the brief](#readings-of-the-brief-and-assumptions)
- [Known limitations](#known-limitations)
- [What I would improve](#what-i-would-improve-with-more-time)
- [AI notes](AI_NOTES.md)

---

## Quick start

Requires Docker with Compose v2.

```sh
git clone <repository-url> room-booking-app   # the URL of this repository
cd room-booking-app
cp .env.example .env
docker compose up --build
```

Open **http://localhost:5173**. On first start the backend applies migrations and creates the demo users and rooms.

### Demo logins

| Username | Password |
| --- | --- |
| `user1`, `user2`, `user3` | the value of `DEMO_USER_PASSWORD` in your `.env` |

`.env` is copied from `.env.example`, where `DEMO_USER_PASSWORD=demo-pass-2026`. That is a **local demo value**, like every other value in that file. Change it in `.env` and restart the backend to use another. Nothing secret is committed, and `.env` is git-ignored.

Demo rooms: Conference Room A (10 people), Meeting Room B (6), Focus Room (4).

### Ports

| Service | Address |
| --- | --- |
| App (React, Vite dev server) | http://localhost:5173 |
| API (Django, for direct API checks) | http://localhost:8000/api/… |
| PostgreSQL | not published; reachable only inside the Compose network |

The browser only talks to `localhost:5173`. Vite proxies `/api` to Django, so the app is single-origin and needs no CORS ([ADR 0004](docs/adr/0004-session-auth-same-origin-no-cors.md)).

### Running the tests

```sh
docker compose run --rm backend pytest          # backend: 184 tests, always on PostgreSQL
docker compose run --rm frontend npm test       # frontend: 61 tests, run with TZ=America/New_York
```

Other checks:

```sh
docker compose run --rm backend python manage.py makemigrations --check --dry-run   # models and migrations agree
docker compose run --rm frontend npx vite build --outDir /tmp/build                 # production build
```

The backend test settings **refuse to run on anything but PostgreSQL**, because the booking guarantees live in PostgreSQL constraints.

---

## What it does: the booking rules

How each numbered rule in the brief is met:

| # | Rule | How |
| --- | --- | --- |
| 1 | Username/password login; demo users | Django auth, passwords hashed (PBKDF2); idempotent `seed_demo` on start |
| 2 | A Room has a name and a capacity | Unique name and capacity > 0, enforced by PostgreSQL |
| 3 | A Booking has room, title, start, end, Booker | The Booker is always the session User, never a request field |
| 4 | 15 minutes to 4 hours; not in the past | Duration is a database CHECK (inclusive). "Not in the past" is checked by the API against the server clock; starting exactly now is allowed |
| 5 | Never double-booked; 10:00–11:00 and 11:00–12:00 don't clash | PostgreSQL exclusion constraint on half-open `[start, end)` ranges per Room, for active bookings |
| 6 | Holds under simultaneous requests | The constraint decides, not application code. Demonstrated by a threaded test on real PostgreSQL |
| 7 | Only the Booker cancels; a cancelled slot can be rebooked | Cancel marks the Booking cancelled and keeps the row; the constraint ignores cancelled bookings |
| 8 | Doha time whatever the computer is set to | Stored in UTC; API and UI always speak `Asia/Qatar` |
| 9 | A clear reason when a booking is refused | Every error has a plain-English `message`, e.g. "Conference Room A is already booked 10:00–11:00." |
| 10 | Viewing a busy Day stays fast | Index-backed queries, constant query count, paginated; see [Performance](#performance) |

### Doha time

- Times are stored as `timestamptz` (UTC).
- The API **accepts only times with a UTC offset**, e.g. `2026-10-20T10:00:00+03:00`. A bare `10:00` is refused as ambiguous.
- Times must be whole minutes.
- The API answers in `+03:00`.
- The frontend formats and builds every time explicitly in `Asia/Qatar`, never in the browser's zone. Its tests run with the process timezone set to New York to prove it.
- A **Day** (`?date=YYYY-MM-DD`) runs from Doha midnight to the next Doha midnight. A Day's schedule includes every booking that **overlaps** it, so a booking from 22:00 to 01:00 appears on both days.
- [ADR 0005](docs/adr/0005-store-utc-speak-doha-time.md).

### Cancelling

- Only the **Booker** may cancel. Anyone else gets `403 not_booker`.
- There is **no time limit**: a Booker may cancel a booking that has started or ended. The brief's only cancellation rule is "only the person who made a booking", so no stricter rule was added.
- Cancelling marks the row `cancelled` with `cancelled_at`, and does not delete it. The history stays answerable, and the slot is freed for rebooking.
- Cancelling again, or cancelling an unknown id, gives `404`.
- The UI asks for confirmation inside the app before cancelling.
- [ADR 0002](docs/adr/0002-cancel-is-a-status-change.md).

---

## Main design decisions

Each is recorded, with its reasons and the alternatives considered, in [`docs/adr/`](docs/adr/).

- **The database prevents double-booking** ([0001](docs/adr/0001-database-exclusion-constraint-prevents-double-booking.md)):
  - A PostgreSQL `EXCLUDE USING gist (room_id WITH =, tstzrange(start_time, end_time, '[)') WITH &&) WHERE (status = 'active')`, using `btree_gist`.
  - A check in application code alone has a race window; row locks or `SERIALIZABLE` need every code path to cooperate.
  - The API's pre-check exists only to give a friendly message.
- **Cancelling is a status change** ([0002](docs/adr/0002-cancel-is-a-status-change.md)): history is kept, and the constraint simply ignores cancelled rows.
- **Rules live in the database where possible** ([0003](docs/adr/0003-not-in-the-past-is-enforced-by-the-api-only.md)):
  - Duration, end after start, non-blank title, valid status, `cancelled_at` matching status, unique Room names and positive capacity are all CHECK or UNIQUE constraints.
  - "Not in the past" cannot be: a CHECK that depends on "now" would turn valid rows invalid as time passes and break restores. So the API enforces it.
- **Session cookies, not tokens** ([0004](docs/adr/0004-session-auth-same-origin-no-cors.md)). Why this suits a React app served from the same origin:
  - The browser sends the session cookie by itself, so the React code never holds a token in memory or `localStorage`.
  - The cookie is `HttpOnly`, so a script injected into the page cannot read the session.
  - Django's built-in CSRF protection covers the one weakness of cookies.
  - Logout is real: the server ends the session.
  - Single origin through the Vite proxy, so CORS is never enabled.
- **Store UTC, speak Doha time** ([0005](docs/adr/0005-store-utc-speak-doha-time.md)): offset-required input, `Asia/Qatar` everywhere, and a Day means overlap.
- **One API shape** ([0006](docs/adr/0006-api-shape-errors-and-pagination.md)): resources returned without a wrapper, one error envelope, a fixed set of status codes, paginated lists.
- **Exact version pins** ([0007](docs/adr/0007-stack-and-version-pins.md)): DRF's compatibility with Django 5.2 was checked, not assumed.

---

## API

Every endpoint except the CSRF bootstrap and login needs a logged-in User.

| Method | Path | Success |
| --- | --- | --- |
| GET | `/api/auth/csrf/` | `200`, sets the `csrftoken` cookie |
| POST | `/api/auth/login/` | `200 {"user": {"id", "username"}}` |
| POST | `/api/auth/logout/` | `204` |
| GET | `/api/auth/me/` | `200 {"id", "username"}` |
| GET | `/api/rooms/` | `200`, paginated Rooms by name |
| GET | `/api/bookings/?room=<id>&date=YYYY-MM-DD` | `200`, a Room's Day schedule (active bookings overlapping that Doha Day, in start order) |
| GET | `/api/bookings/?mine=true` | `200`, the session User's upcoming active bookings, in start order |
| POST | `/api/bookings/` | `201`, the new Booking |
| DELETE | `/api/bookings/{id}/` | `204` (cancel) |

**Filters:** `GET /api/bookings/` takes exactly one form, either `room` + `date` or `mine=true`. A missing, partial or mixed form gives `400`.

**Pagination:** lists are paginated as `{"count", "next", "previous", "results"}`, 100 per page by default and at most. An optional `page_size` lowers it. The frontend follows `next` until it is null.

**Creating a booking:**

```json
POST /api/bookings/
{"room_id": 1, "title": "Product Review", "start_time": "2026-10-20T10:00:00+03:00", "end_time": "2026-10-20T11:00:00+03:00"}
```

The returned Booking:

```json
{"id": 2, "room": {"id": 1, "name": "Conference Room A", "capacity": 10}, "title": "Product Review",
 "start_time": "2026-10-20T10:00:00+03:00", "end_time": "2026-10-20T11:00:00+03:00",
 "booked_by": {"id": 1, "username": "user1"}, "created_at": "…"}
```

**Validation order:**
1. The request's shape.
2. The Room exists.
3. End is after start.
4. 15 minutes ≤ duration ≤ 4 hours.
5. Not in the past.
6. Overlap check, which gives `409`.
7. Insert, guarded by the database constraint.

Steps 1–5 give `400` naming the field.

### Errors

Every error from every endpoint has one shape ([ADR 0006](docs/adr/0006-api-shape-errors-and-pagination.md)):

```json
{"error": {"code": "booking_conflict", "message": "Conference Room A is already booked 10:00–11:00.", "fields": {}}}
```

| Status | `code` | When |
| --- | --- | --- |
| `400` | `validation_error` | Invalid input or filters; malformed JSON. `fields` has per-field messages |
| `400` | `invalid_credentials` | Wrong username or password (one message for both, so usernames can't be probed) |
| `401` | `not_authenticated` | No session; sent with `WWW-Authenticate: Session` |
| `403` | `csrf_failed` | Missing, invalid or stale CSRF token, including on login |
| `403` | `not_booker` | Cancelling someone else's booking |
| `404` | `not_found` | Unknown id or URL, a booking that is no longer active, a page out of range |
| `405` | `method_not_allowed` | e.g. `PUT` or `PATCH` on a booking; there is no edit, so cancel and book again |
| `409` | `booking_conflict` | The slot overlaps an active booking in that Room |
| `415` | `unsupported_media_type` | A body that is not JSON |
| `429` | `throttled` | "Too many login attempts. Try again in N seconds." |
| `400`/`403`/`500` | `bad_request` / `permission_denied` / `server_error` | Errors Django raises outside the API layer (e.g. a bad `Host` header) or an unexpected failure. No internal detail is sent |

Only PostgreSQL's exclusion violation (SQLSTATE `23P01`) **from the named constraint** `no_overlapping_active_bookings` becomes `409`. Every other database error propagates.

The one exception: a **deadlock** (`40P01`) on the insert. Two truly simultaneous overlapping inserts can deadlock inside the exclusion check. The insert is retried up to 3 times, which in practice gives the real answer, `409` or `201`. A deadlock on every attempt still ends in a `500`; a deadlock is never itself reported as a conflict ([ADR 0001](docs/adr/0001-database-exclusion-constraint-prevents-double-booking.md)).

---

## Security

### Authentication and CSRF

- DRF's session authentication answers logged-out requests with `403` by default. A small subclass makes it `401` with `WWW-Authenticate: Session`, and gives CSRF failures their own code.
- DRF skips CSRF for anonymous requests, so **login runs the CSRF check itself** before reading any credentials.
- Login rotates the session and the CSRF token.
- The frontend reads the token from the cookie on every unsafe request, so a stale pre-login token is never sent.
- Tests prove a stale token is refused and creates nothing.
- The full flow (bootstrap → login → authenticated `POST`) was also checked in a real browser through the Vite proxy: the token rotated, the stale token was refused with `403 csrf_failed`, and logout led to `401`.

### Login throttle

- Five attempts per minute per client.
- Behind the Vite proxy every request arrives from one address, so DRF trusts exactly one proxy hop (`NUM_PROXIES=1`) and keys on the address the proxy appends.
- **Accepted trade-off:** a client calling port `8000` directly could forge `X-Forwarded-For` to dodge the limit. Trusting no header instead would make all users share one limit.

### Production settings

`DEBUG` is off unless `DJANGO_DEBUG` in `.env` turns it on; local development uses `DJANGO_DEBUG=True`. **`DEBUG=False` requires HTTPS in front of the app.** It enables:
- an HTTP→HTTPS redirect;
- HSTS for one year with `includeSubDomains` (this assumes a deployment controls every subdomain of its host);
- `Secure` session and CSRF cookies.

Over plain HTTP, port `8000` then redirects every request. Deployment is out of scope; this describes what a deployment would need.

Two settings are deliberately left off:
- **HSTS preload** (Django check W021): it is hard to reverse and needs a real domain.
- **`SECURE_PROXY_SSL_HEADER`**: it is only safe once a known HTTPS proxy strips client-supplied headers. Until then Django must see HTTPS directly; behind a TLS-terminating proxy the redirect would loop.

### Checklist

Each item was verified by command or test; how each was checked is recorded in [`.scratch/room-booking-app/evidence/12-security-checklist.md`](.scratch/room-booking-app/evidence/12-security-checklist.md).

- No CORS.
- PostgreSQL not published.
- No secrets committed.
- `manage.py check --deploy` clean except the documented W021.
- No raw SQL in application code (ORM only).
- No `dangerouslySetInnerHTML` (React escapes every title and username).
- Passwords never logged.
- One error envelope everywhere.
- An AI-assisted security review of the whole app (Claude Code's security reviewer) found no blocking issues: no access to other users' data beyond the intended shared schedule, and clients cannot set the Booker, status or cancellation time. This was not a human security audit.

---

## Database, indexes and evidence

The bookings table as PostgreSQL 17 reports it (`\d bookings_booking`) and the SQL of its migrations are saved in [`.scratch/room-booking-app/evidence/06-bookings-table.txt`](.scratch/room-booking-app/evidence/06-bookings-table.txt) and [`06-bookings-sqlmigrate.txt`](.scratch/room-booking-app/evidence/06-bookings-sqlmigrate.txt). Tests also check the live catalog: the exclusion constraint's exact definition, every named CHECK, and exactly the indexes below.

| Index | Serves | Why it's kept |
| --- | --- | --- |
| `no_overlapping_active_bookings` (GiST) | The no-double-booking rule | Enforces ADR 0001. It does **not** serve the list queries: they filter plain columns, while it indexes a range expression |
| `booking_room_start_active_idx` (partial btree, active) | A Room's Day schedule | Without it, the Day count becomes a full table scan (4.167 ms instead of 0.006 ms) |
| `booking_user_start_active_idx` (partial btree, active) | My Bookings | Without it, My Bookings becomes a full table scan (page 5.333 ms instead of 0.134 ms) |

Django's default single-column foreign-key indexes were removed (migration `0002`) because nothing used them.

## Performance

How it was checked: `EXPLAIN (ANALYZE, BUFFERS)` on the exact SQL the API sends, on 105,332 seeded bookings (3 years, 20 rooms, 50 users, 6,513 crossing midnight). Every number below is quoted from a saved, verbatim plan in [`.scratch/room-booking-app/evidence/13-performance.md`](.scratch/room-booking-app/evidence/13-performance.md).

```sh
docker compose exec backend python manage.py seed_perf_data --reset --days 1095   # development only
docker compose exec backend python manage.py explain_booking_queries
docker compose exec backend python manage.py explain_booking_queries --without-index booking_room_start_active_idx
docker compose exec backend python manage.py seed_perf_data --delete               # remove the data again
```

**Finding: an exact lower bound.**
- The first queries read a Room's or User's whole history through the index.
- Both now add `start_time > window start − 4 hours`. This changes no result, because the database guarantees no booking lasts over 4 hours.
- The index now reads only rows that can match, so the cost does not grow with history:

| Query | Index entries read, before → after (matching) | Time, before → after |
| --- | --- | --- |
| Day schedule count | 2,321 → **9** (9) | 0.113 → 0.006 ms |
| Day schedule page | — | 0.200 → 0.051 ms |
| My Bookings count | 1,831 → **968** (968) | 0.454 → 0.213 ms |
| My Bookings page | — | 0.515 → 0.134 ms |

Measured three times, each after a fresh `ANALYZE`; the ranges are stable. Two tests pin a maximum-length booking at each bound's edge.

**No query per row:**
- A Day's schedule takes 5 queries and My Bookings takes 4, whatever the number of bookings.
- Tests assert the count stays the same for 5 and 50 bookings, and removing `select_related` fails them.

**Correction:** an earlier claim ("9.7 ms → 0.057 ms") came from a run with stale planner statistics, and is recorded as wrong. The fair gain is shown above.

---

## Tests, and why these ones

184 backend tests (pytest on PostgreSQL) and 61 frontend tests (Vitest). They are written at three agreed seams:

1. **The HTTP API on PostgreSQL:**
   - every booking rule at its boundaries (15 minutes and 4 hours inclusive, 14 minutes and 4 hours 1 minute refused, start exactly now allowed);
   - touching slots allowed;
   - validation order;
   - cancel permissions;
   - Doha Day edges, including the 00:30 Doha case that is still "yesterday" in UTC, and bookings crossing midnight;
   - pagination past 100;
   - a constant query count;
   - the error envelope on every endpoint;
   - 401, CSRF (including stale tokens) and the login throttle.
2. **The database directly:** ORM writes that **skip all validation** must be refused by PostgreSQL. Each refusal is checked by the name of the constraint that fired. This checks the brief's "invalid data cannot be saved, even by code that skips your validation" for every constraint listed under Main design decisions.
3. **Frontend modules:**
   - the Doha time module, with the timezone set to New York to prove browser-independence;
   - the API client: it never sends a stale CSRF token, follows `next`, parses the error envelope, and follows pagination links only within its own origin.

**The race test** ([`test_concurrent_booking.py`](backend/tests/test_concurrent_booking.py)):
- Two threads, each with its own PostgreSQL connection and a different logged-in User, book the same slot at the same instant.
- One variant forces both past the application's pre-check, so only the constraint can stop the second.
- Result in every run (15 consecutive runs of the file, each with about 40 races): one `201`, one `409`, one active booking.
- **With the constraint removed, it fails with `[201, 201]`.** That shows the database, not the application, prevents double-booking.
- It also found a real bug: a deadlock surfaced as a `500`. The deadlock retry now handles it.

**Why I trust the tests:** important tests were checked by breaking the code on purpose and confirming they fail. For example: letting anyone cancel, hard-deleting instead of soft-cancelling, a UTC Day instead of a Doha Day, mapping any database error to `409`, caching the CSRF token, or tightening a query bound.

---

## Readings of the brief and assumptions

Where the brief was open, these choices were made and recorded:

- **The CSRF endpoint is anonymous**, although the brief says only login is. Login itself needs a CSRF token, and that endpoint returns no data.
- **"Not in the past" is the one rule the database cannot enforce** (see above).
- **The frontend follows every page of a list.** Lists are always filtered by the database first, to one Room's Day or one User's upcoming bookings, so this never loads the whole table.
- **The Booker may cancel any of their active bookings, at any time.** The brief sets no time limit.
- **A failed login returns `400 invalid_credentials`.** `401` means "no session".
- **Field names:** creating a booking takes `room_id`, while the list filter is `room`.
- **Limits:**
  - titles are trimmed and at most 200 characters;
  - duration limits are inclusive;
  - starting exactly now is allowed;
  - an unknown `room` in the filter is a `400`.
- **Bookings may cross midnight;** there are no office hours. Capacity is informational only.
- **Times must be whole minutes;** the time pickers use 15-minute steps by default.
- **Cancelling asks for confirmation** inside the app before it takes effect.
- **All logged-in Users can see every booking's title and Booker,** as a shared office calendar.

## Known limitations

- **With `DEBUG=True`** (local development), Django shows its own error pages for errors outside the API layer instead of the JSON envelope. Production runs with `DEBUG` off.
- **Unknown extra query parameters are ignored, not refused.** A stricter rule was not approved.
- **The login throttle can be dodged on port `8000`** by forging `X-Forwarded-For`; see Security.
- **Time pickers follow the browser's locale,** so they may show AM/PM. The values sent are always Doha time.
- **Mobile layout is basic:** the sidebar becomes a top bar at 720 px wide or narrower.

## What I would improve with more time

- **A per-User rate limit on creating bookings.** The security review pointed out that a logged-in User could script rapid booking attempts against the exclusion constraint, costing CPU, including the deadlock retries. It was **deliberately left out**, by decision, because the approved spec only throttles login ([`.scratch/room-booking-app/evidence/12-security-checklist.md`](.scratch/room-booking-app/evidence/12-security-checklist.md)). A scoped DRF throttle on booking creation would cap it.
- **A production setup:** a WSGI server, a built frontend served behind an HTTPS proxy, and `SECURE_PROXY_SSL_HEADER` configured for that proxy.
- **Edit a booking** instead of cancel-and-rebook.
- **Component and end-to-end browser tests.** Browser checks were done manually with Playwright during development.
- **A 24-hour time picker** independent of the browser's locale.
- **Stricter query-parameter validation,** if wanted.

---

## Project map

| Path | Contents |
| --- | --- |
| `backend/` | Django project: `config/` (settings, URLs, error handlers), `accounts/` (auth, demo seed), `rooms/`, `bookings/` (model, constraints, `services.py` rules, `queries.py`, dev-only perf commands), `tests/` |
| `frontend/` | React + Vite: `src/api/` (CSRF-aware client), `src/auth/`, `src/pages/`, `src/components/`, `src/utils/dohaTime.js` |
| [`GLOSSARY.md`](GLOSSARY.md) | The domain vocabulary |
| [`docs/adr/`](docs/adr/) | Architecture decision records 0001–0007 |
| [`docs/design/`](docs/design/) | The eight design visuals, and which details the ADRs supersede ([README](docs/design/README.md)) |
| [`docs/brief/`](docs/brief/) | The original assignment brief |
| [`.scratch/room-booking-app/`](.scratch/room-booking-app/) | The implementation spec, the 14 tickets, and the evidence (constraint output, security checklist, query plans) |
| [`AI_NOTES.md`](AI_NOTES.md) | How AI was used, where it was wrong, and what was decided independently |

The Git history shows the work ticket by ticket in small commits.
