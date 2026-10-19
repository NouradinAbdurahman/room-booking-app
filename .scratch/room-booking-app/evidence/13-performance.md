# Ticket 13: performance evidence

Measured on 2026-10-19 on PostgreSQL 17 (Docker Compose) with three years of seeded data.

## How to reproduce

```sh
docker compose exec backend python manage.py seed_perf_data --reset --days 1095   # 20 rooms, 50 users, ~105k bookings
docker compose exec backend python manage.py explain_booking_queries                # plans + queries per request
docker compose exec backend python manage.py explain_booking_queries --without-index booking_room_start_active_idx
docker compose exec backend python manage.py explain_booking_queries --without-index booking_user_start_active_idx
docker compose exec backend python manage.py seed_perf_data --delete               # remove the perf data again
```

`seed_perf_data` is development only:
- It refuses to run unless `DEBUG` is on or `--force` is passed.
- It uses a fixed random seed.
- Every row passes the database constraints.
- It runs `ANALYZE`, so the planner has real statistics.

`explain_booking_queries` runs `EXPLAIN (ANALYZE, BUFFERS)` on exactly the SQL the API sends (`bookings.queries`), for the busiest Room-and-Day and the User with the most upcoming Bookings. `--without-index` drops one index inside a transaction that is always rolled back.

Dataset: `Bookings: 105332 (90465 active). Day schedule: room 55 (Perf Room 11) on 2026-11-15. My Bookings: perf_user_048.`

## What was found

1. **The GiST exclusion index protects, but does not serve the list queries.**
   - The Day query filters on the plain `start_time` and `end_time` columns. The GiST index is built on the expression `tstzrange(start_time, end_time, '[)')`, so PostgreSQL cannot use it for that filter.
   - With the `(room_id, start_time)` B-tree dropped, the Day count fell back to a sequential scan of the whole table.
   - Rewriting the query as a range overlap (`tstzrange(...) && tstzrange(day)`) did reach the GiST index, but only for the count, and matching the range without the room. The page query still got a poor plan (18 ms, 90,456 rows discarded). Rejected.
2. **The original queries scanned history.**
   - `start_time < day_end` makes the B-tree read a Room's whole past.
   - On three years of data the planner also switched the Day page to a worse plan: 9.7 ms, discarding 47,546 rows to return 9.
   - My Bookings discarded every past Booking of the User (863 rows).
3. **Fix: an exact lower bound** (`start_time > window_start − 4 hours`).
   - It changes no result, because the database guarantees no Booking lasts longer than 4 hours (`booking_duration_15min_to_4h`).
   - The B-trees now read only the rows that can match.
   - Tests pin a 4-hour Booking at the edge of each bound. Tightening either bound by an hour fails them.

| Query (3 years, ~105k bookings) | Before | After |
| --- | --- | --- |
| Day schedule page | 9.710 ms, 47,546 rows discarded | **0.057 ms**, 0 discarded |
| Day schedule count | 0.128 ms, 2,312 rows discarded | **0.006 ms**, 0 discarded |
| My Bookings page | 863 past rows discarded | **0.131 ms**, 0 bookings discarded |

## Index decision (evidence, not assumption)

| Index | Kept? | Why |
| --- | --- | --- |
| `no_overlapping_active_bookings` (GiST) | Yes | Enforces "no Double-booking" (ADR 0001). Not used by the list queries. |
| `booking_room_start_active_idx` | **Yes** | Without it, the Day count becomes a full table scan: 4.592 ms, 105,323 rows discarded. |
| `booking_user_start_active_idx` | **Yes** | Without it, My Bookings becomes a full table scan: 4.604 ms, 104,364 rows discarded. |

No index was added or removed, so there is no migration. The change is the lower bound in `bookings/queries.py`.

## No query per row

Day schedule: HTTP 200, 9 of 9 bookings returned in 5 queries
My Bookings: HTTP 200, 100 of 968 bookings returned in 4 queries

These are constant regardless of the number of Bookings:
- Day schedule: 5 queries (session, user, room check, count, page).
- My Bookings: 4 queries (session, user, count, page).

`tests/test_day_schedule_api.py` and `tests/test_my_bookings_api.py` assert the count does not grow (5 vs 50 Bookings), and removing `select_related` fails them.

## Representative plans (after the fix), verbatim

Full output of the final run: `13-explain-full.txt`.

Day schedule page:
```
Limit  (cost=19.70..19.70 rows=2 width=158) (actual time=0.040..0.041 rows=9 loops=1)
  Buffers: shared hit=10
  ->  Sort  (cost=19.70..19.70 rows=2 width=158) (actual time=0.039..0.040 rows=9 loops=1)
        Sort Key: bookings_booking.start_time, bookings_booking.id
        Sort Method: quicksort  Memory: 27kB
        Buffers: shared hit=10
        ->  Nested Loop  (cost=15.57..19.69 rows=2 width=158) (actual time=0.023..0.032 rows=9 loops=1)
              Buffers: shared hit=7
              ->  Seq Scan on rooms_room  (cost=0.00..1.29 rows=1 width=41) (actual time=0.003..0.003 rows=1 loops=1)
                    Filter: (id = 55)
                    Rows Removed by Filter: 22
                    Buffers: shared hit=1
              ->  Hash Join  (cost=15.57..18.38 rows=2 width=117) (actual time=0.019..0.026 rows=9 loops=1)
                    Hash Cond: (auth_user.id = bookings_booking.user_id)
                    Buffers: shared hit=6
                    ->  Seq Scan on auth_user  (cost=0.00..2.53 rows=53 width=45) (actual time=0.001..0.004 rows=53 loops=1)
                          Buffers: shared hit=2
                    ->  Hash  (cost=15.54..15.54 rows=2 width=72) (actual time=0.015..0.015 rows=9 loops=1)
                          Buckets: 1024  Batches: 1  Memory Usage: 9kB
                          Buffers: shared hit=4
                          ->  Index Scan using booking_room_start_active_idx on bookings_booking  (cost=0.42..15.54 rows=2 width=72) (actual time=0.004..0.006 rows=9 loops=1)
                                Index Cond: ((room_id = 55) AND (start_time > '2026-11-14 17:00:00+00'::timestamp with time zone) AND (start_time < '2026-11-15 21:00:00+00'::timestamp with time zone))
                                Filter: (end_time > '2026-11-14 21:00:00+00'::timestamp with time zone)
                                Buffers: shared hit=4
Planning:
  Buffers: shared hit=33
Planning Time: 0.125 ms
Execution Time: 0.057 ms
```

Day schedule count:
```
Aggregate  (cost=15.55..15.56 rows=1 width=8) (actual time=0.003..0.003 rows=1 loops=1)
  Buffers: shared hit=4
  ->  Index Scan using booking_room_start_active_idx on bookings_booking  (cost=0.42..15.54 rows=2 width=0) (actual time=0.002..0.003 rows=9 loops=1)
        Index Cond: ((room_id = 55) AND (start_time > '2026-11-14 17:00:00+00'::timestamp with time zone) AND (start_time < '2026-11-15 21:00:00+00'::timestamp with time zone))
        Filter: (end_time > '2026-11-14 21:00:00+00'::timestamp with time zone)
        Buffers: shared hit=4
Planning Time: 0.023 ms
Execution Time: 0.006 ms
```

My Bookings page:
```
Limit  (cost=7.25..676.54 rows=100 width=158) (actual time=0.058..0.121 rows=100 loops=1)
  Buffers: shared hit=143
  ->  Incremental Sort  (cost=7.25..2998.96 rows=447 width=158) (actual time=0.058..0.117 rows=100 loops=1)
        Sort Key: bookings_booking.start_time, bookings_booking.id
        Presorted Key: bookings_booking.start_time
        Full-sort Groups: 4  Sort Method: quicksort  Average Memory: 33kB  Peak Memory: 33kB
        Buffers: shared hit=143
        ->  Nested Loop  (cost=0.56..2978.88 rows=447 width=158) (actual time=0.018..0.090 rows=101 loops=1)
              Buffers: shared hit=140
              ->  Nested Loop  (cost=0.42..2964.20 rows=447 width=117) (actual time=0.013..0.062 rows=101 loops=1)
                    Buffers: shared hit=102
                    ->  Index Scan using booking_user_start_active_idx on bookings_booking  (cost=0.42..2955.94 rows=447 width=72) (actual time=0.009..0.040 rows=101 loops=1)
                          Index Cond: ((user_id = 152) AND (start_time > '2026-10-19 10:07:40.476702+00'::timestamp with time zone))
                          Filter: (end_time > '2026-10-19 14:07:40.476702+00'::timestamp with time zone)
                          Buffers: shared hit=100
                    ->  Materialize  (cost=0.00..2.67 rows=1 width=45) (actual time=0.000..0.000 rows=1 loops=101)
                          Buffers: shared hit=2
                          ->  Seq Scan on auth_user  (cost=0.00..2.66 rows=1 width=45) (actual time=0.003..0.003 rows=1 loops=1)
                                Filter: (id = 152)
                                Rows Removed by Filter: 52
                                Buffers: shared hit=2
              ->  Memoize  (cost=0.15..0.19 rows=1 width=41) (actual time=0.000..0.000 rows=1 loops=101)
                    Cache Key: bookings_booking.room_id
                    Cache Mode: logical
                    Hits: 82  Misses: 19  Evictions: 0  Overflows: 0  Memory Usage: 3kB
                    Buffers: shared hit=38
                    ->  Index Scan using rooms_room_pkey on rooms_room  (cost=0.14..0.18 rows=1 width=41) (actual time=0.000..0.000 rows=1 loops=19)
                          Index Cond: (id = bookings_booking.room_id)
                          Buffers: shared hit=38
Planning:
  Buffers: shared hit=16
Planning Time: 0.075 ms
Execution Time: 0.131 ms
```

My Bookings count:
```
Aggregate  (cost=1615.06..1615.07 rows=1 width=8) (actual time=0.311..0.311 rows=1 loops=1)
  Buffers: shared hit=544
  ->  Bitmap Heap Scan on bookings_booking  (cost=41.51..1613.95 rows=447 width=0) (actual time=0.067..0.286 rows=968 loops=1)
        Recheck Cond: ((user_id = 152) AND (start_time > '2026-10-19 10:07:40.476702+00'::timestamp with time zone) AND ((status)::text = 'active'::text))
        Filter: (end_time > '2026-10-19 14:07:40.476702+00'::timestamp with time zone)
        Heap Blocks: exact=536
        Buffers: shared hit=544
        ->  Bitmap Index Scan on booking_user_start_active_idx  (cost=0.00..41.40 rows=898 width=0) (actual time=0.039..0.039 rows=968 loops=1)
              Index Cond: ((user_id = 152) AND (start_time > '2026-10-19 10:07:40.476702+00'::timestamp with time zone))
              Buffers: shared hit=8
Planning Time: 0.017 ms
Execution Time: 0.313 ms
```

Without booking_room_start_active_idx: Day schedule count:
```
Aggregate  (cost=4260.97..4260.98 rows=1 width=8) (actual time=4.581..4.582 rows=1 loops=1)
  Buffers: shared hit=1891
  ->  Seq Scan on bookings_booking  (cost=0.00..4260.97 rows=2 width=0) (actual time=2.761..4.578 rows=9 loops=1)
        Filter: ((end_time > '2026-11-14 21:00:00+00'::timestamp with time zone) AND (start_time > '2026-11-14 17:00:00+00'::timestamp with time zone) AND (start_time < '2026-11-15 21:00:00+00'::timestamp with time zone) AND (room_id = 55) AND ((status)::text = 'active'::text))
        Rows Removed by Filter: 105323
        Buffers: shared hit=1891
Planning Time: 0.053 ms
Execution Time: 4.592 ms
```

Without booking_user_start_active_idx: My Bookings count:
```
Aggregate  (cost=3998.76..3998.77 rows=1 width=8) (actual time=4.074..4.074 rows=1 loops=1)
  Buffers: shared hit=1891
  ->  Seq Scan on bookings_booking  (cost=0.00..3997.64 rows=447 width=0) (actual time=0.091..4.049 rows=968 loops=1)
        Filter: ((end_time > '2026-10-19 14:07:42.15136+00'::timestamp with time zone) AND (start_time > '2026-10-19 10:07:42.15136+00'::timestamp with time zone) AND (user_id = 152) AND ((status)::text = 'active'::text))
        Rows Removed by Filter: 104364
        Buffers: shared hit=1891
Planning Time: 0.016 ms
Execution Time: 4.076 ms
```
