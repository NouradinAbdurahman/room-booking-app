# API shape: bare resources, one error envelope, fixed status codes, paginated lists

## Endpoints

```
GET    /api/auth/csrf/                          no auth
POST   /api/auth/login/                         no auth
POST   /api/auth/logout/
GET    /api/auth/me/
GET    /api/rooms/
GET    /api/bookings/?room=<id>&date=YYYY-MM-DD  a Day's schedule for a Room
GET    /api/bookings/?mine=true                 the current User's Upcoming bookings
POST   /api/bookings/
DELETE /api/bookings/{id}/                      cancel (ADR 0002)
```

`GET /api/bookings/` requires exactly one of the two filter forms. Anything else returns `400`.

- **Day filter:** returns every active booking that overlaps the Doha Day, including bookings that cross midnight (ADR 0005), ordered by `start_time`.
- **`mine=true`:** returns only the session user's active bookings with `end_time > now`, ordered by `start_time`. The user comes from the session, never from a parameter.

There is no update endpoint. To change a booking, cancel it and book again.

## Responses

A successful response returns the resource itself, with no `{"message", "data"}` wrapper. A booking is returned as:

```json
{"id": 2, "room": {"id": 1, "name": "Conference Room A", "capacity": 10}, "title": "Product Review",
 "start_time": "2026-10-18T10:00:00+03:00", "end_time": "2026-10-18T11:00:00+03:00",
 "booked_by": {"id": 1, "username": "user1"}, "created_at": "..."}
```

Lists use page-number pagination: `{"count", "next", "previous", "results"}`, with a default and maximum page size of 100. In normal use a Day's schedule fits in one page. The frontend still follows `next` until it is null, so correctness never depends on an assumed maximum number of bookings per Day.

Every error response from every endpoint, including DRF's built-in authentication, permission, throttle and validation errors, uses one shape. A custom exception handler produces it:

```json
{"error": {"code": "booking_conflict", "message": "Conference Room A is already booked 10:00–11:00.", "fields": {}}}
```

| Status | Meaning |
| ------ | ------- |
| `200` / `201` / `204` | OK / booking created / booking cancelled |
| `400` | Validation failed, including every booking rule except overlap (`fields` holds per-field messages) |
| `401` | Not logged in |
| `403` | Not your booking, or CSRF failure |
| `404` | Not found, or not an active booking |
| `409` | Only: the slot conflicts with an existing active booking |
| `429` | Too many login attempts |

The frontend shows `message` to the user as the refusal reason (brief, rule 9).

## Consequences

- Indexes match the two booking queries. This was confirmed with `EXPLAIN ANALYZE` (ticket 13; evidence in `.scratch/room-booking-app/evidence/13-performance.md`):
  - The Day query is served by the btree on `(room_id, start_time)` for active bookings, and My Bookings by `(user_id, start_time)`. Both are kept; without either, the query falls back to a full table scan.
  - The exclusion constraint's GiST index enforces the no-overlap rule but does not serve these queries. They filter the plain columns, while the GiST index is built on the range expression. A range-overlap rewrite that reaches the GiST index was measured and was slower.
  - Both queries add `start_time > window start − 4 hours`. This is exact, because the database caps a Booking at 4 hours. It lets the btree scans skip older history instead of reading and discarding it; their cost still depends on how many bookings match and on the plan PostgreSQL chooses.
- To verify during implementation:
  - A test for each endpoint confirms its error responses use this envelope and status codes.
  - Pagination is checked against seeded data with more than 100 bookings overlapping one Day, including bookings that cross midnight.
  - A query-count test stays constant as bookings grow, so there is no query per row.
  - The `EXPLAIN ANALYZE` results go in the README.
