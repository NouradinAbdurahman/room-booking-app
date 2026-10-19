Status: ready-for-agent

# Spec: Room Booking App

Sources of truth: `GLOSSARY.md`, `docs/adr/0001`–`0007`, `docs/design/README.md` with the eight visuals, and the brief at `docs/brief/Room-Booking-Take-Home-Test.pdf`. Where this spec and an ADR disagree, the ADR wins and this spec is wrong. Vocabulary follows the glossary: User, Booker, Room, Booking, Slot, Active booking, Cancelled booking, Upcoming booking, Cancel, Double-booking, Conflict, Refusal, Doha time, Day.

## Problem Statement

The Doha office has a few meeting Rooms, and people keep double-booking them. Nobody can reliably see who has a Room when, so two teams turn up for the same Room at the same time. Times get confused because colleagues' laptops are set to different timezones, and when a booking goes wrong nobody is told why.

## Solution

A small web app where a logged-in User can:

- see the Rooms and any Room's schedule for a chosen Day in Doha time;
- book a Room for a Slot;
- see their own Upcoming bookings and Cancel them.

The server enforces every rule, and the database itself makes a Double-booking impossible, even when two Users book the same Slot at the same moment. Every Refusal tells the User exactly why. All times are shown and entered in Doha time, whatever the User's device is set to.

## User Stories

### Logging in and out

1. As a User, I want to log in with my username and password, so that I can use the app.
2. As a User, I want a clear "Invalid username or password." message when my login fails, so that I know to retry.
3. As a User, I want the login message to not reveal whether the username exists, so that attackers can't discover valid usernames.
4. As a User, I want to stay logged in while I move between pages and after reloading, so that I don't have to log in repeatedly.
5. As a User, I want to log out, so that nobody else can use my session on a shared computer.
6. As a User whose session has expired, I want to be sent back to the login page, so that I'm not left looking at errors.
7. As an evaluator, I want demo Users and Rooms to exist already, so that I can try the app without a sign-up page.
8. As a security reviewer, I want repeated failed logins to be slowed down, so that passwords can't be brute-forced.
9. As a security reviewer, I want passwords stored only as hashes and never logged, so that a leak of the database or logs exposes no passwords.

### Rooms

10. As a User, I want to see a list of all Rooms with their name and Capacity, so that I can choose a suitable Room.
11. As a User, I want to open a Room to see its schedule, so that I can decide when to book it.

### A Room's Day schedule

12. As a User, I want to see every Active booking for a Room on a chosen Day, so that I can see when it is free.
13. As a User, I want the schedule to open on today's Day in Doha time, so that the most relevant Day shows first.
14. As a User, I want to step to the previous or next Day, or pick a date, so that I can plan ahead.
15. As a User, I want each Booking to show its title, its start and end in Doha time, and its Booker, so that I know who has the Room.
16. As a User, I want free gaps between Bookings shown as "Available", so that I can spot open Slots at a glance.
17. As a User, I want a Booking that crosses midnight to appear on both Days it touches, so that late meetings are never hidden.
18. As a User, I want Cancelled bookings to disappear from the schedule, so that I only see Slots that are really taken.
19. As a User, I want the schedule to stay fast on a busy Day, so that I'm not kept waiting.

### Booking a Room

20. As a User, I want to book the Room I'm viewing by giving a title, a start and an end, so that the Room is mine for that Slot.
21. As a User, I want to enter times in Doha time even if my laptop is set to another timezone, so that I book the time I mean.
22. As a User, I want the form to show the Booking's duration as I edit, so that I can see whether it fits the 15-minute to 4-hour limit.
23. As a User, I want time pickers in 15-minute steps by default, so that common times are quick to enter.
24. As a User, I want a Booking that ends at 10:00 and another that starts at 10:00 to both be accepted, so that back-to-back meetings work.
25. As a User, I want a clear Refusal when my Slot overlaps an existing Booking, naming the Room and the conflicting times, so that I can pick another time.
26. As a User, I want a clear Refusal when my Booking is shorter than 15 minutes or longer than 4 hours, so that I know the limits.
27. As a User, I want a clear Refusal when my Booking starts in the past, so that I don't book a Slot that has gone.
28. As a User, I want a clear Refusal when the end is not after the start, or the title is blank, so that I can fix the form.
29. As a User, I want to see a success message and the new Booking in the schedule straight away, so that I know it worked.
30. As a User, I want to be able to book a Slot that crosses midnight, so that late events can be booked.
31. As a User whose colleague books the same Slot at the same moment, I want exactly one of us to succeed and the other to get a clear Conflict message, so that the Room is never double-booked.

### My Bookings and cancelling

32. As a Booker, I want a My Bookings page listing my Upcoming bookings across all Rooms and Days, so that I can find the ones I made.
33. As a Booker, I want to Cancel one of my Bookings, so that the Room is freed for others.
34. As a Booker, I want to confirm before a Cancel takes effect, so that I don't cancel by accident.
35. As a Booker, I want to Cancel from both the Room schedule and My Bookings, so that I can do it wherever I see the Booking.
36. As a User, I want the Cancel action shown only on my own Bookings, so that the UI doesn't offer something I can't do.
37. As a Booker, I want to be able to Cancel any of my Active bookings, even one that has started, so that the app follows the brief's only cancellation rule.
38. As a User, I want to book a Slot that was freed by a Cancel, so that freed Slots are actually usable.
39. As a Booker, I want a Cancelled booking to leave My Bookings straight away, so that the list stays accurate.

### Rules enforced by the server

40. As the office, I want the server to refuse a request to Cancel someone else's Booking even if the UI is bypassed, so that only the Booker can Cancel.
41. As the office, I want every booking rule checked on the server, so that a modified frontend can't break them.
42. As the office, I want the database itself to reject Double-bookings and invalid Bookings, so that even code that skips validation can't save bad data.
43. As the office, I want a history of who booked and who cancelled, so that disputes can be answered.
44. As the office, I want every API endpoint except the CSRF bootstrap and login to require a logged-in User, so that schedules aren't public.
45. As a security reviewer, I want unsafe requests without a valid CSRF token refused, so that other websites can't act as the User.
46. As a security reviewer, I want no cross-origin access enabled at all, so that no other origin can call the API with the User's cookies.
47. As a security reviewer, I want no secrets in the repo except clearly marked local demo values, so that cloning the repo leaks nothing.
48. As a security reviewer, I want production-safe settings whenever debug mode is off, so that a misconfigured deploy is safe by default.

### The API for developers and reviewers

49. As a frontend developer, I want every error to have the same shape with a code, a message and field messages, so that the UI handles errors one way.
50. As a reviewer, I want correct HTTP status codes for each outcome, so that the API is predictable.
51. As a reviewer, I want every list endpoint paginated, so that responses stay bounded as data grows.
52. As a reviewer, I want the endpoints listed in the README, so that I can explore the API.
53. As a reviewer, I want the API to refuse ambiguous times that have no UTC offset, so that times are never misread.

### Running and reviewing the project

54. As an evaluator, I want to start the whole app with a few commands from the README, so that I can review it quickly.
55. As an evaluator, I want to run all the tests with one documented command each, against real PostgreSQL, so that I can trust the results.
56. As an evaluator, I want the README to explain the main design decisions, the indexes and how performance was checked, so that I can judge the reasoning.
57. As an evaluator, I want `AI_NOTES.md` to say how AI was used, where it was wrong and what was decided independently, so that I can see how the candidate works with AI.
58. As an evaluator, I want a Git history of small, meaningful commits, so that I can follow how the work progressed.

## Implementation Decisions

### 1. Project structure and pinned versions (ADR 0007, visual 2)

- One repository with a `backend` Django project and a `frontend` Vite + React app. The root holds the Compose file, `.env.example`, `.gitignore`, `README.md` and `AI_NOTES.md`.
- The Django project is split into a `config` module (settings, root URLs, ASGI/WSGI), a **rooms** app and a **bookings** app.
- Inside bookings there are three layers:
  - serializers for HTTP-shaped validation;
  - a **booking service module** that owns the business rules, the friendly overlap pre-check, the insert and cancel transactions, and the translation of an exclusion violation into a Conflict;
  - thin views.
- Authentication endpoints sit in a small module, either in `config` or a tiny `accounts` app, using Django's built-in `User` model.
- The frontend is organised into pages, components, an **API client module** (all HTTP, CSRF and pagination) and a **Doha time module** (all date and time logic).
- Pins:

  | Component | Version |
  | --- | --- |
  | PostgreSQL | `postgres:17` |
  | Python | 3.13 |
  | Django | `5.2.18` |
  | djangorestframework | `3.18.3` |

- Other Python dependencies are pinned exactly: the PostgreSQL driver, pytest, pytest-django, and nothing else unless it's needed. There is **no** `django-cors-headers`.
- Frontend dependencies are locked by a committed `package-lock.json`. The frontend uses React with Vite, a router, and Vitest. No UI kit is required; plain CSS with design tokens is enough.

### 2. Data model, constraints, indexes, migrations and concurrency (ADRs 0001, 0002, 0003, 0006; visual 3)

**Room**

| Field | Type and rule |
| --- | --- |
| `id` | bigint |
| `name` | varchar, unique, not blank |
| `capacity` | positive integer |
| `created_at`, `updated_at` | timestamps |

**Booking**

| Field | Type and rule |
| --- | --- |
| `id` | bigint |
| `room` | FK → Room, protect on delete |
| `user` | FK → User (the Booker), protect on delete |
| `title` | varchar, max 200, not blank after trimming |
| `start_time`, `end_time` | `timestamptz` |
| `status` | `active` or `cancelled`, default `active` |
| `cancelled_at` | nullable timestamp |
| `created_at`, `updated_at` | timestamps |

Each fact is stored once: Room details live only on Room, and User details only on the auth user.

**Database constraints**, declared on the models so that they appear in migrations:

- CHECK `end_time > start_time`.
- CHECK `end_time - start_time` is between 15 minutes and 4 hours, inclusive.
- CHECK the title is not blank after trimming.
- CHECK `capacity > 0`.
- UNIQUE room `name`.
- CHECK `status` is one of the two values.
- CHECK (`status = 'cancelled'`) ⇔ (`cancelled_at IS NOT NULL`).
- **EXCLUDE** `no_overlapping_active_bookings`: `room_id WITH =`, `tstzrange(start_time, end_time, '[)') WITH &&`, `WHERE status = 'active'`, using GiST. A migration operation creates the `btree_gist` extension before the constraint.

"Cannot start in the past" is **not** a database constraint (ADR 0003). The booking service checks it against the server clock.

**Indexes:**
- The GiST index created by the exclusion constraint.
- A partial btree on `(room_id, start_time)` for active bookings, used by the Day schedule.
- A partial btree on `(user_id, start_time)` for active bookings, used by My Bookings.
- The unique index on room name.

`EXPLAIN ANALYZE` on seeded data decides whether the Day btree earns its place. The README reports the outcome.

**Concurrency:**
- The insert runs in a transaction.
- If the exclusion constraint is violated, the error is caught. It counts as a Conflict **only** if SQLSTATE is `23P01` **and** the constraint name is `no_overlapping_active_bookings`. The service then re-reads the conflicting Active booking, if any, to build the message, and raises a Conflict, which becomes `409`.
- Every other database error propagates unchanged, with one exception: a deadlock (SQLSTATE `40P01`) on the insert itself is retried a few times. The retry then gets the real outcome: `409` via the rule above, or `201`. A deadlock is never itself reported as a Conflict (ADR 0001).
- There is no application-level locking.
- The friendly pre-check before the insert exists only so the common case gets a good message.

**Cancel:**
- A single conditional update moves an active booking to cancelled, setting `cancelled_at` and `updated_at`.
- If no active row with that id exists, the result is `404`.
- If the row exists but belongs to another User, the result is `403`.

### 3. Authentication, CSRF, throttling and security settings (ADR 0004, visual 7)

- The default permission is "authenticated". Only the CSRF bootstrap and login allow anonymous access.
- **The project's session authentication class**, a small subclass of DRF's `SessionAuthentication`, is the only authentication class. It exists to fix two behaviours of DRF 3.18.3 that were verified against its source:
  1. **401, not 403, when logged out.** DRF turns "not authenticated" into `403` whenever the first authentication class supplies no `WWW-Authenticate` header, and stock `SessionAuthentication` supplies none. The subclass returns the header value `Session`, so DRF responds `401` with `WWW-Authenticate: Session`. The value must not be `Basic`, which would make browsers show a login pop-up. CSRF behaviour is unchanged.
  2. **A distinct CSRF failure.** Stock DRF raises a generic `PermissionDenied("CSRF Failed: …")`. The subclass keeps DRF's exact CSRF check, but raises a dedicated CSRF-failed exception (a `403` subtype with code `csrf_failed`). The error handler then maps it without matching on message text.
- **CSRF on authenticated requests:** unchanged from DRF. Every unsafe method from a logged-in session runs Django's CSRF check.
- **CSRF bootstrap** sets the `csrftoken` cookie, which is readable by JavaScript. The response body may echo the token.
- **Login is explicitly CSRF-protected.** DRF skips CSRF for anonymous requests, because `authenticate()` returns early, and every DRF view is `csrf_exempt`. So the login view **calls the authentication class's CSRF check itself, before reading any credentials**. A login without a valid token is refused with `403 csrf_failed`, and the credentials are never checked. DRF's throttle runs before the view, so a refused login still counts towards the 5-per-minute limit. That is intended.
- **After a successful login**, the view calls Django's `login`. That rotates the session id **and the CSRF token**, sending a new `csrftoken` cookie in the login response. The view returns the User. Request parameters are marked sensitive so the password is never logged.
- **Logout** requires a session, so it goes through the authentication class's CSRF check.
- **Logout** ends the session and is CSRF-protected.
- **Me** returns the current User.
- DRF scoped throttle on login only, at 5 attempts per minute per client. Excess attempts get `429`.
- **Cookies:**
  - session cookie: `HttpOnly`, `SameSite=Lax`;
  - CSRF cookie: not `HttpOnly`, `SameSite=Lax`;
  - both `Secure` when `DEBUG` is off.
- **Settings:**
  - `CSRF_TRUSTED_ORIGINS` includes `http://localhost:5173`.
  - `ALLOWED_HOSTS` comes from the environment.
  - `DEBUG` comes from the environment and defaults to off.
  - `SECRET_KEY` comes from the environment and is required when `DEBUG` is off.
  - HSTS, `SECURE_CONTENT_TYPE_NOSNIFF` and frame denial are on when `DEBUG` is off.
- No CORS middleware or settings exist.
- The User is always taken from the session. No endpoint accepts a user id.
- Only the ORM is used, apart from the extension migration, so all SQL is parameterised. React escapes all output, and `dangerouslySetInnerHTML` is never used.

### 4. API contract (ADR 0006, visual 6)

| Method | Path | Auth | Success |
| --- | --- | --- | --- |
| GET | `/api/auth/csrf/` | anonymous | `200` + cookie |
| POST | `/api/auth/login/` | anonymous | `200` `{"user": {"id", "username"}}` |
| POST | `/api/auth/logout/` | user | `204` |
| GET | `/api/auth/me/` | user | `200` `{"id", "username"}` |
| GET | `/api/rooms/` | user | `200` paginated Rooms ordered by name |
| GET | `/api/bookings/?room=<id>&date=YYYY-MM-DD` | user | `200` paginated Active bookings overlapping that Doha Day, ordered by `start_time` |
| GET | `/api/bookings/?mine=true` | user | `200` paginated Upcoming bookings of the session User, ordered by `start_time` |
| POST | `/api/bookings/` | user | `201` Booking |
| DELETE | `/api/bookings/{id}/` | user | `204` |

- **Room shape:** `{"id", "name", "capacity"}`.
- **Booking shape:** `{"id", "room": {"id", "name", "capacity"}, "title", "start_time", "end_time", "booked_by": {"id", "username"}, "created_at"}`. Times are ISO-8601 in `+03:00`.
- **Create request:** `{"room_id", "title", "start_time", "end_time"}`.
- **Pagination:** `{"count", "next", "previous", "results"}`, page-number based. An optional `page_size` parameter defaults to and is capped at 100.
- **Bookings list filters:** exactly one filter form must be supplied.
  - `room` + `date` together, or `mine=true` alone.
  - Missing, mixed or partial filters return `400`.
  - An unknown `room` returns `400` with a field error.
  - An invalid `date` returns `400`.
- **Error envelope:** `{"error": {"code", "message", "fields"}}`. It is used for every non-2xx response, including DRF's built-in authentication, permission, not-found, method-not-allowed, throttle and parse errors, and Django's CSRF failure.

| Status | `code` | When |
| --- | --- | --- |
| `400` | `validation_error` | Any rule except overlap, bad filters, malformed body (`fields` filled) |
| `400` | `invalid_credentials` | Wrong username or password |
| `401` | `not_authenticated` | No session; sent with `WWW-Authenticate: Session` |
| `403` | `csrf_failed` | Missing, invalid or stale CSRF token, including on login |
| `403` | `not_booker` | Cancelling someone else's Booking |
| `404` | `not_found` | Unknown id, or Booking not active |
| `405` | `method_not_allowed` | e.g. `PUT` or `PATCH` on a Booking |
| `409` | `booking_conflict` | The Slot overlaps an Active booking, from the pre-check or the database |
| `429` | `throttled` | Login rate exceeded |

- **Messages are plain English and suitable for the UI.** The Conflict message names the Room and the conflicting times in Doha time ("Conference Room A is already booked 10:00–11:00."). If the conflicting Booking can't be re-read, it falls back to "…is already booked at that time."

### 5. Booking rules and Doha time (ADRs 0002, 0003, 0005)

**Validation order on create:**
1. Shape: all fields present, the title is not blank and at most 200 characters, and the times are ISO-8601 **with an offset** in whole minutes (seconds and fractions must be zero).
2. The Room exists.
3. `end_time > start_time`.
4. The duration is between 15 minutes and 4 hours inclusive.
5. `start_time >= now` on the server clock.
6. Overlap pre-check, which gives `409`.
7. Insert, protected by the constraint.

Every failure in steps 1–5 is `400` with field messages.

**Further rules:**
- A booking may start at exactly "now". Boundaries are inclusive: exactly 15 minutes and exactly 4 hours are both valid.
- There are no office hours, and Bookings may cross midnight.
- Capacity is informational only.
- **Cancel:** only the Booker, any Active booking regardless of time, freeing the Slot, with the row kept. There is no edit; to change a Booking, Cancel it and book again.

**Doha time:**
- Settings: `USE_TZ=True`, `TIME_ZONE="Asia/Qatar"`. The database stores UTC.
- The API serialises times in `Asia/Qatar` (`+03:00`).
- A Day for `date=D` is the window [D 00:00 Asia/Qatar, D+1 00:00 Asia/Qatar). The filter is `start_time < day_end AND end_time > day_start`.
- "Upcoming" means `end_time > now`.
- The zone is always named `Asia/Qatar`, never hard-coded as `+03:00` in logic.

**Frontend:**
- All formatting and parsing goes through the Doha time module, which uses `Intl` with `timeZone: 'Asia/Qatar'`.
- It builds request times as offset-aware ISO strings from the User's chosen Doha date and time, without ever going through the browser's local zone.
- "Today" means today in Doha.

### 6. React screens and design (visual 8, `docs/design/README.md`)

**Layout:** a dark navy sidebar with the app name and icon, Rooms, My Bookings and Logout. The content area is light grey and white. Primary buttons are bright blue. Booking blocks use pastel colours. Success messages are green and error messages are red. On mobile the sidebar collapses into a top bar; the mobile layout is kept basic. Colours are defined once as CSS design tokens.

**Screens:**

1. **Login.** Username, password with a show/hide toggle, a Login button, and the error message from the API.
2. **Rooms.** Cards showing each Room's name and Capacity, linking to the Room's schedule.
3. **Room schedule.**
   - A "Back to Rooms" link and the Room header with its Capacity.
   - A date stepper (previous, picker, next) that defaults to today in Doha.
   - Bookings in start-time order, each with title, Doha times and Booker. Times are clipped visually at the Day's edges, but the real times are still shown.
   - "Available" placeholders for gaps.
   - A Cancel action on the User's own Bookings.
   - A "Book This Room" button.
   - The selected date is reflected in the URL.
4. **Create booking.** A dialog over the schedule with title, start date and time, end date and time (15-minute steps by default), live duration with the "15 minutes to 4 hours" hint, Cancel and Book buttons, and the API's error message or field errors. On success the schedule refreshes and a success message shows.
5. **My Bookings.** A table of Upcoming bookings (Room, Title, Date, Time, Cancel), with pagination followed automatically.

**API client and the CSRF token.** The API client never caches the CSRF token:
- On every unsafe request it reads the **current** value of the `csrftoken` cookie at send time and puts it in the `X-CSRFToken` header.
- On app start it calls the CSRF bootstrap if no cookie is present.
- After login, the next unsafe request automatically uses the rotated token from the login response's cookie, so a stale pre-login token is never sent.
- After logout, it calls the bootstrap again before the next login.

**Behaviour:**
- **Cancel** asks for confirmation inside the app, not with the browser's `confirm()`.
- **Any `401`** sends the User to Login.
- **Lists** are fetched by following `next` until it is null.
- **No list** is ever filtered or computed client-side beyond showing the gaps.

### 7. Docker Compose, demo data and environment

**Services:**
- `db`: `postgres:17`, a named volume and a healthcheck. **No published ports.**
- `backend`: the Python 3.13 image. On start it waits for the healthy `db`, runs migrations, runs an idempotent demo-seed command, and serves on `0.0.0.0:8000`, published as `8000`.
- `frontend`: the Node LTS image running the Vite dev server on `5173`, published as `5173`. It proxies `/api` to `backend:8000`, keeping the `Host` and `Origin` headers in a way that passes Django's CSRF origin check. That behaviour must be verified.

**Demo seed (idempotent):**
- Users `user1`, `user2` and `user3`, sharing one demo password read from the environment. `.env.example` sets it to a value clearly marked as a local demo value.
- Rooms "Conference Room A" (10), "Meeting Room B" (6) and "Focus Room" (4).
- No demo Bookings are required.

**Performance data:** a separate development-only command seeds many Bookings across Rooms, Days and Users, including Bookings that cross midnight. It is used for the `EXPLAIN ANALYZE` evidence in the README and is never run automatically.

**Environment variables:**

| Variable | Notes |
| --- | --- |
| `DJANGO_SECRET_KEY` | |
| `DJANGO_DEBUG` | |
| `DJANGO_ALLOWED_HOSTS` | |
| `CSRF_TRUSTED_ORIGINS` | |
| `POSTGRES_DB` | |
| `POSTGRES_USER` | |
| `POSTGRES_PASSWORD` | |
| `POSTGRES_HOST` | |
| `POSTGRES_PORT` | |
| `DEMO_USER_PASSWORD` | |

`.env.example` is committed with demo values that are clearly marked. `.env` is git-ignored.

**Setup:** copy `.env.example` to `.env`, then `docker compose up --build`, then open `http://localhost:5173`.

### 8. README, AI_NOTES and Git workflow

**README sections:**
- Quick start
- Demo logins
- Running the tests (backend and frontend commands)
- Endpoint table
- Error format
- Design decisions, a few lines each, linking the ADRs:
  - constraint-based overlap prevention;
  - soft cancel;
  - which rules live in the database and why "not in the past" doesn't;
  - session authentication with no CORS;
  - Doha time;
  - My Bookings;
  - pagination.
- Indexes and why
- How performance was checked: `EXPLAIN ANALYZE` output summaries and the query-count tests
- Which tests were written and why
- Assumptions and readings of the brief: Booker may Cancel at any time; the CSRF endpoint is anonymous; login failure is `400`
- What I'd improve with more time

**`AI_NOTES.md`:**
- The tools used and for which parts.
- At least two places where AI was wrong or weak, and what was done. Real examples from design:
  - an unproven "max 96 bookings per Day" claim;
  - an added "no cancelling after start" rule the brief didn't ask for;
  - the inconsistent error and response shapes in the AI-made API visual;
  - plus any found during implementation.
- **One genuine decision made independently of the AI, with the reasoning.** It must be a real decision from this project, and it is **not chosen by this spec**. The author provides or confirms the actual example when the file is written. Neither the implementer nor the AI may invent one or fill it in.

**Git:** small commits, in roughly this order:
1. docs
2. scaffold and Compose
3. models and constraints
4. auth
5. rooms API
6. bookings API
7. error handler
8. tests per area
9. frontend shell
10. screens
11. frontend tests
12. README and AI notes

Each commit leaves the app runnable where practical. There is never a single big final commit.

## Testing Decisions

**What a good test is:** it drives the system only through a public seam (HTTP, the ORM, or a module's exports) and asserts observable outcomes: status codes, response bodies, database state, and returned values. It does not assert private functions, serializer internals or query text. Tests use the glossary's vocabulary in their names.

**Prior art:** none. The repo has no code yet, so these tests set the patterns.

### Seam 1: backend HTTP API on real PostgreSQL 17 (primary)

pytest-django with DRF's API client, run inside Compose. The test settings refuse to start unless the engine is PostgreSQL. CSRF tests use a client with CSRF checks enforced.

- **Auth:** all of these use the CSRF-enforcing client.
  - **T-AUTH-1:** every protected endpoint and method returns `401`, the envelope with `not_authenticated`, and a `WWW-Authenticate: Session` header when logged out. It never returns `403`.
  - **T-AUTH-2:** full flow. The CSRF bootstrap sets the cookie. Login with that token returns `200` and a **new** `csrftoken` cookie different from the bootstrap one. A `POST` booking with the **new** token returns `201`.
  - **T-AUTH-3:** stale token. After login, a `POST` booking sent with the **pre-login** token returns `403 csrf_failed`, and no Booking is created.
  - **T-AUTH-4:** login CSRF. A login with no token, or a wrong token, returns `403 csrf_failed` even with correct credentials, and no session is created.
  - **T-AUTH-5:** an authenticated `POST` or `DELETE` without a token returns `403 csrf_failed`, and nothing changes.
  - **T-AUTH-6:** a wrong password returns `400 invalid_credentials`, and the message doesn't reveal whether the username exists.
  - **T-AUTH-7:** the 6th login attempt within a minute returns `429 throttled`.
  - **T-AUTH-8:** logout returns `204`. The next call returns `401`.
- **Create:**
  - Valid → `201`, with times returned as `+03:00`.
  - Exactly 15 minutes and exactly 4 hours → valid. 14 minutes, or 4 hours 1 minute → `400`.
  - End ≤ start → `400`. Start in the past → `400`. Blank title → `400`.
  - No offset → `400`. Non-zero seconds → `400`. Unknown room → `400`.
- **Overlap:**
  - An overlapping Slot → `409 booking_conflict`, with the message naming the Room and the times.
  - Touching edges (10:00 end and 10:00 start) → both `201`.
  - Overlap in a *different* Room → `201`.
- **Cancel and rebook:**
  - The Booker cancels → `204`, the row still exists as cancelled, and the same Slot can be booked again → `201`.
  - A non-Booker → `403 not_booker`.
  - Cancelling twice → `404`.
  - Cancelling a Booking that has started → `204`.
- **Day schedule:**
  - Returns exactly the Active bookings overlapping the Doha Day. A 22:00–01:00 Booking appears on both Days.
  - A Booking at 00:30 Doha appears on that Doha date even though it is the previous date in UTC.
  - Cancelled bookings and other Rooms are excluded.
  - Results are ordered by `start_time`.
- **My Bookings:** returns only the session User's Active bookings with `end_time > now`, and never another User's.
- **Filters:** missing, mixed or partial filters → `400`.
- **Pagination:**
  - My Bookings with 150 Upcoming bookings returns 100 + 50 across two pages, with a working `next`. Asking for `page_size` above 100 is capped.
  - The Day schedule with a small `page_size`, over a Day that includes Bookings crossing midnight, returns every overlapping Booking exactly once across all pages.
- **Error envelope:** for each endpoint, the error responses it can produce use the envelope and the documented codes, including `405` and `404`.
- **Query count:** the Day schedule and My Bookings use a constant number of queries for 5 versus 50 Bookings, so there is no query per row.
- **Concurrency:** a transactional test starts two threads behind a barrier, each with its own client and User. Both `POST` the same Slot. Exactly one `201` and one `409`, and exactly one Active booking exists. The test repeats a few iterations to reduce flakiness. It must run on PostgreSQL.

### Seam 2: database constraints via the ORM (skipping validation)

Each of these must raise a database integrity error:
- creating an overlapping Active booking directly;
- a duration under 15 minutes or over 4 hours;
- end ≤ start;
- a blank title;
- a capacity of 0;
- a duplicate room name;
- a cancelled status with no `cancelled_at`, or the reverse.

Each of these must be accepted:
- an overlapping *cancelled* booking;
- touching Slots.

The migration check: the constraint `no_overlapping_active_bookings` exists in the PostgreSQL catalog and includes the active-only predicate.

### Seam 3: frontend pure modules (Vitest, with `TZ=America/New_York`)

- **Doha time module:**
  - Formats a UTC instant as Doha date and time.
  - Builds an offset-aware ISO string from a Doha date and time, and the result is the same whatever the process timezone is.
  - Computes today's Doha date near midnight UTC, where the dates differ.
  - Computes duration.
  - Clips a midnight-crossing Booking to a Day's edges.
- **API client:**
  - Follows `next` across pages and concatenates the results.
  - Sends the CSRF header on unsafe methods and none on `GET`.
  - **Stale-token test:** the fake cookie value changes between two unsafe requests, simulating rotation on login. The second request must carry the **new** value. This test fails if the client caches the token.
  - Calls the CSRF bootstrap when no cookie is present.
  - Turns the error envelope into a message plus field errors.
  - Reports `401` so the app can redirect to Login.

The tests use a fake `fetch`.

### Not automated (evidence recorded in the README)

- `EXPLAIN ANALYZE` of both booking queries over the performance seed.
- `\d` on the bookings table showing the constraint.
- A manual check of the CSRF flow through the Vite proxy in a real browser.

## Acceptance Criteria

Each criterion is met when the referenced tests pass or the referenced evidence exists. "Seam 1 › Overlap" means the Overlap bullet group under Seam 1 in Testing Decisions.

### Functional

1. A logged-in User can list Rooms with name and Capacity. *(Seam 1 › Pagination and Error envelope; manual check in the UI.)*
2. The Day schedule returns exactly the Active bookings overlapping the chosen Doha Day, including Bookings that cross midnight and the 00:30 case. *(Seam 1 › Day schedule.)*
3. Valid Bookings are created, and Bookings of exactly 15 minutes and exactly 4 hours are accepted. *(Seam 1 › Create.)*
4. Bookings that are too short, too long, start in the past, have end ≤ start, a blank title, a time without an offset, or non-zero seconds are refused with `400` and a field message. *(Seam 1 › Create.)*
5. Overlapping Bookings in the same Room are refused with `409 booking_conflict`, naming the Room and the times. Touching Slots and other Rooms are accepted. *(Seam 1 › Overlap.)*
6. Only the Booker can Cancel, at any time. A Cancel keeps the row, frees the Slot for rebooking, and a second Cancel returns `404`. *(Seam 1 › Cancel and rebook.)*
7. My Bookings shows only the session User's Upcoming bookings. *(Seam 1 › My Bookings.)*

### Database

8. Two simultaneous requests for the same Slot give exactly one `201` and one `409`, on PostgreSQL. *(Seam 1 › Concurrency.)*
9. Every database constraint rejects invalid rows written without validation. Overlapping *cancelled* rows and touching rows are accepted. *(Seam 2.)*
10. The migration creates `btree_gist` and `no_overlapping_active_bookings` with the active-only predicate on PostgreSQL 17. *(Seam 2 › migration check; `\d` output in the README.)*
11. Only the named exclusion violation becomes `409`; other database errors are not reported as Conflicts. *(Seam 1 › Overlap; code review against ADR 0001.)*
12. Tests refuse to run on any database other than PostgreSQL. *(The test settings guard.)*

### Security

13. Every endpoint except the CSRF bootstrap and login returns `401` with `WWW-Authenticate: Session` when logged out. *(T-AUTH-1.)*
14. Login refuses a missing or wrong CSRF token with `403 csrf_failed`. *(T-AUTH-4.)*
15. The bootstrap → login → authenticated `POST` flow works with the rotated token, and a stale pre-login token is refused. *(T-AUTH-2, T-AUTH-3; Seam 3 › stale-token test; manual check through the Vite proxy.)*
16. Unsafe authenticated requests without a CSRF token are refused. *(T-AUTH-5.)*
17. Login is throttled. A failed login doesn't reveal whether the username exists, and passwords are never logged. *(T-AUTH-6, T-AUTH-7; code review.)*
18. No CORS package or setting exists. PostgreSQL has no published port. No secrets are committed apart from marked demo values. Settings are production-safe when `DEBUG` is off. *(Review of the Compose file, settings and `.env.example`.)*

### API

19. Every non-2xx response from every endpoint uses `{"error": {"code", "message", "fields"}}`, with the documented status and code. *(Seam 1 › Error envelope; Seam 3 › error parsing.)*
20. Lists are paginated at a maximum of 100, and `next` returns every item exactly once. *(Seam 1 › Pagination; Seam 3 › follows `next`.)*

### Performance

21. The Day schedule and My Bookings use a constant number of queries regardless of the number of Bookings. *(Seam 1 › Query count.)*
22. Both booking queries use an index on the performance seed. *(`EXPLAIN ANALYZE` output summarised in the README.)*

### Time

23. All times shown and entered are Doha time, whatever the device's timezone. *(Seam 3 › Doha time module, run with `TZ=America/New_York`; Seam 1 › times returned as `+03:00`.)*

### UI

24. The five screens exist and match visual 8: navy sidebar, light content area, blue primary buttons. Each Refusal's message is shown to the User. *(Manual check against `docs/design/8- Frontend Design.png`.)*

### Running and documentation

25. A fresh clone runs with: copy `.env.example`, then `docker compose up --build`. Demo logins work. *(Manual run following the README only.)*
26. The README covers every section listed in Implementation Decisions §8, including the flagged brief/ADR differences and the assumptions. *(Review.)*
27. `AI_NOTES.md` lists the tools used, at least two real AI mistakes with what was done about them, and one genuine independent decision provided by the author. *(Review.)*
28. The Git history shows small, incremental commits. *(`git log`.)*

## Out of Scope

- Sign-up, password reset, emails and notifications.
- Recurring bookings.
- Editing a Booking; Cancel and rebook instead.
- Admin screens for managing Rooms or Users. Django admin may exist but is not part of the deliverable.
- Office hours.
- Capacity enforcement or attendee lists.
- Deployment and production hosting. Production-safe *settings* are in scope.
- CORS.
- Pixel-perfect polish.
- Browser end-to-end tests and component tests.
- Fully dark theming.
- Internationalisation.
- Cancelled-booking history views in the UI. History is kept in the database only.

## Further Notes

### Conflicts between the brief and the ADRs (flagged, not silently changed)

1. **"Every endpoint except login needs a logged-in user" (brief) vs. an anonymous CSRF bootstrap endpoint (ADRs 0004 and 0006).** The CSRF endpoint must be reachable before login, because login itself is CSRF-protected. It returns no data. The README states this exception.
2. **"Database constraints so invalid data cannot be saved" (brief) vs. "not in the past" being enforced by the API only (ADR 0003).** No PostgreSQL CHECK can do this correctly, because rules based on "now" break restores and later updates. The README states this as the one rule the database can't enforce.
3. **"No loading everything into the browser" (brief) vs. the frontend following `next` until it is null (ADR 0006).** Lists are always filtered by the database to one Room's Day or one User's Upcoming bookings. Following pages only completes the requested view; it never loads the whole table.

### Assumptions this spec makes (within the ADRs, to be stated in the README)

- A failed login returns `400 invalid_credentials`, not `401`. `401` is reserved for "no session".
- The create request uses `room_id`, as in visual 6. The list filter uses `room`, as in ADR 0006.
- The title has a maximum of 200 characters.
- Duration boundaries are inclusive.
- A start time equal to "now" is allowed.
- An unknown `room` filter returns `400`, not an empty list.
- A Cancel asks for confirmation in the UI.

### Remaining ambiguity

- Whether the Day btree index adds anything beyond the GiST index will be decided by `EXPLAIN ANALYZE` during implementation. Either way, the README records the outcome.

### Context on the page size

By the duration and no-overlap rules, a single Room can only hold just under 100 Active bookings on one Day. That is why the Day pagination test uses a small `page_size` rather than more than 100 Bookings. The design never relies on this bound.
