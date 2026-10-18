# Design visuals

These eight visuals were made before the design was refined. They are kept as-is. Where a visual disagrees with an ADR in `docs/adr/`, **the ADR wins**. The tables below list exactly what is superseded.

| # | Visual | Status |
| - | ------ | ------ |
| 1 | First Architecture Diagram | Current, except the Compose ports (below) |
| 2 | Repository Structure | Current |
| 3 | Database Schema | Partly superseded |
| 4 | Preventing Double Bookings | Current, except the constraint's `WHERE` clause (below) |
| 5 | Booking Rules and Time Handling | Current |
| 6 | API Design | Partly superseded |
| 7 | Authentication and Security | Partly superseded |
| 8 | Frontend Design | **The UI reference** |

## Superseded details

| Visual | Shows | Now | ADR |
| ------ | ----- | --- | --- |
| 1 | Postgres published on host port `5432` | Postgres is internal to the Compose network. Only `5173` and `8000` are published. | 0004 |
| 3 | `bookings` has no cancellation columns | Adds `status` (`active`/`cancelled`), `cancelled_at`, `updated_at` | 0002 |
| 3, 4 | The exclusion constraint applies to all rows | `... WHERE (status = 'active')`, so cancelling frees the slot | 0001 |
| 3 | Room `name` not unique | Unique constraint on room `name` | 0003 |
| 3 | Index on `user_id` | Index on `(user_id, start_time)` for active bookings, serving My Bookings | 0006 |
| 6 | Booking filters: `room_id` (optional) and `date` (required) | Exactly one of `room` + `date` (Day schedule) or `mine=true` (own Upcoming bookings) | 0006 |
| 6 | Errors as `{"detail": "..."}` | `{"error": {"code", "message", "fields"}}` on every endpoint | 0006 |
| 6 | Successes wrapped in `{"message", "data"}`; lists returned as bare arrays | Bare resources; lists paginated as `{count, next, previous, results}` (max 100) | 0006 |
| 6 | Cancel returns `200` with a message | `204 No Content` | 0002 |
| 6 | `409` = overlap **or rule violation** | `409` = overlap only; rule violations are `400` | 0006 |
| 6 | `created_by` field | `booked_by` (glossary: Booker) | 0006 |
| 6 | `/api/auth/csrf/` returns the token in the body | The SPA reads the `csrftoken` cookie. Returning the token in the body as well is harmless. | 0004 |
| 7 | `CORS_ALLOWED_ORIGINS = ['http://localhost:5173']` | No CORS at all: same origin through the Vite proxy | 0004 |
| 5, 7 | "Only the creator can cancel" | "Only the Booker can cancel", with no time limit | 0002 |

## Frontend reference (visual 8)

The UI matches visual 8 closely, without pixel-perfect polish:

- **Layout:** a dark navy sidebar (Rooms, My Bookings, Logout) next to a light grey and white content area.
- **Colours:** bright-blue primary buttons, pastel booking blocks, and green or red message banners.
- **Screens:** Login, Rooms list, Room Schedule (with a date stepper), Create Booking, and My Bookings.
- **Mobile:** kept basic.
- **Room images:** visual 1 shows room photos; we use visual 8's icons instead.
