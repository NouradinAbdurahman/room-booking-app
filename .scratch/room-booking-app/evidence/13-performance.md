# Ticket 13: performance evidence

Measured on 2026-10-19 on PostgreSQL 17 (Docker Compose). Every number below is quoted from a saved, verbatim `EXPLAIN (ANALYZE, BUFFERS)` output in this folder, all taken on the same data and the same planner statistics.

## How to reproduce

```sh
docker compose exec backend python manage.py seed_perf_data --reset --days 1095
docker compose exec backend python manage.py explain_booking_queries
docker compose exec backend python manage.py explain_booking_queries --without-index booking_room_start_active_idx
docker compose exec backend python manage.py explain_booking_queries --without-index booking_user_start_active_idx
docker compose exec backend python manage.py seed_perf_data --delete
```

**`seed_perf_data`:**
- Development only: it refuses to run with `DEBUG` off unless `--force` is passed.
- Uses a fixed random seed, so the same data is rebuilt every time.
- Every row passes the database constraints.
- Runs `ANALYZE` on every table it touches.
- Output (`13-seed-output.txt`): `Created 20 rooms, 50 users, 105332 bookings (90465 active, 14867 cancelled, 6513 crossing midnight).`

**`explain_booking_queries`:**
- Explains the exact SQL the API sends (`bookings/queries.py`): the page query and the paginator's exact `COUNT`.
- Uses the busiest Room-and-Day and the User with the most upcoming Bookings: `Bookings: 105332 (90465 active). Day schedule: room 115 (Perf Room 11) on 2026-11-15. My Bookings: perf_user_048.`
- `--without-index` accepts only an index of the bookings table and drops it inside a transaction that is always rolled back. It holds a table lock while running, so use it on a development database only.

**Files:**

| File | Contents |
| --- | --- |
| `13-explain-before.txt` | The queries as first written (commit `465e6c1`) |
| `13-explain-after.txt` | The current queries |
| `13-explain-after-without-room-btree.txt` | Current queries, `booking_room_start_active_idx` dropped for the run |
| `13-explain-after-without-user-btree.txt` | Current queries, `booking_user_start_active_idx` dropped for the run |
| `13-explain-rejected-gist-rewrite.txt` | The rejected range-overlap alternative |

## Finding 1: the queries read all history; an exact lower bound fixes it

**The problem.**
- `start_time < day_end` lets the `(room_id, start_time)` index find every Booking a Room ever had before that Day. `user_id = X` does the same across a User's whole past.
- So the index reads grow with every day of history.

**The fix: `start_time > window_start − 4 hours`.**
- It changes no result. The database guarantees no Booking lasts longer than 4 hours (`booking_duration_15min_to_4h`, which exists from the table's first migration), so a Booking that starts earlier has already ended.
- Tests pin a 4-hour Booking at the edge of each bound. Tightening either bound by an hour fails them.

Index entries read (from the plans):

| Query | Before | After | Bookings that match |
| --- | --- | --- | --- |
| Day count | 2321 | 9 | 9 |
| My Bookings count | 1831 | 968 | 968 |

Execution time:

| Query | Before | After |
| --- | --- | --- |
| Day page | 0.200 ms | 0.051 ms |
| Day count | 0.113 ms | 0.006 ms |
| My Bookings page | 0.515 ms | 0.134 ms |
| My Bookings count | 0.454 ms | 0.213 ms |

Stability check: before and after were also measured three times, each after a fresh `ANALYZE` (a new random sample). Ranges:

| Query | Before | After |
| --- | --- | --- |
| Day page | 0.174–0.188 ms | 0.050–0.055 ms |
| Day count | 0.105–0.124 ms | 0.005–0.007 ms |
| My Bookings page | 0.316–0.380 ms | 0.121–0.145 ms |
| My Bookings count | 0.397–0.425 ms | 0.205–0.232 ms |

**Correction.**
- Commit `6916e89` claimed "Day page 9.7 ms → 0.057 ms". That "before" figure came from a run where the seed had refreshed statistics only for the bookings table. The planner then believed there were 3 Rooms and chose a poor plan.
- With fresh statistics on every table (the seed now does this), the honest gain is the 2–20 times shown above.
- What does not depend on statistics: the bounded index scans skip older history instead of reading and discarding it. Their cost still depends on how many bookings match and on the plan PostgreSQL chooses.

## Finding 2: index decision (evidence, not assumption)

The GiST exclusion index (`no_overlapping_active_bookings`) prevents Double-booking. That is proven by:
- `tests/test_booking_constraints.py`: overlaps refused with SQLSTATE `23P01`, plus catalog checks of its definition;
- `tests/test_concurrent_booking.py`: simultaneous requests, where removing the constraint gives `[201, 201]`.

**It does not serve the list queries.**
- They filter the plain `start_time` and `end_time` columns, while the GiST index is built on the expression `tstzrange(start_time, end_time, '[)')`.
- Rewriting the Day query as a range overlap reaches the GiST index, but matches the range without the room, so it reads every Room's Bookings on that Day. It came out slower: page 0.573 ms and count 0.170 ms, against 0.051 ms and 0.006 ms. **Rejected.**

| Index | Kept? | Evidence when dropped |
| --- | --- | --- |
| `no_overlapping_active_bookings` (GiST) | Yes | Enforces the no-Double-booking rule (ADR 0001); not used by the list queries |
| `booking_room_start_active_idx` | **Yes** | Day count 4.167 ms instead of 0.006 ms: `->  Seq Scan on bookings_booking  (actual time=2.288..4.163 rows=9 loops=1)` |
| `booking_user_start_active_idx` | **Yes** | My Bookings page 5.333 ms and count 4.737 ms, instead of 0.134 ms and 0.213 ms |

No index was added or removed, so there is no migration. The only change is the lower bound in `bookings/queries.py`.

## Finding 3: no query per row

Day schedule: HTTP 200, 9 of 9 bookings returned in 5 queries
My Bookings: HTTP 200, 100 of 968 bookings returned in 4 queries

The count stays constant regardless of the number of Bookings:
- Day schedule: 5 queries (session, user, room check, count, page).
- My Bookings: 4 queries (session, user, count, page).

`tests/test_day_schedule_api.py` and `tests/test_my_bookings_api.py` assert the count does not grow (5 vs 50 Bookings), and removing `select_related` fails them.

## Bookings-table scans in the current plans (verbatim lines from `13-explain-after.txt`)

```
Day schedule: page: ->  Index Scan using booking_room_start_active_idx on bookings_booking  (actual time=0.005..0.006 rows=9 loops=1)
Day schedule: count: ->  Index Scan using booking_room_start_active_idx on bookings_booking  (actual time=0.002..0.003 rows=9 loops=1)
My Bookings: page: ->  Index Scan using booking_user_start_active_idx on bookings_booking  (actual time=0.008..0.045 rows=101 loops=1)
My Bookings: count: ->  Bitmap Heap Scan on bookings_booking  (actual time=0.050..0.188 rows=968 loops=1)
My Bookings: count: ->  Bitmap Index Scan on booking_user_start_active_idx  (actual time=0.030..0.030 rows=968 loops=1)
```
