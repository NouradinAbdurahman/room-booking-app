# Store UTC, speak Doha time explicitly, and define a Day as overlap with a Doha calendar day

Users see and enter times in Doha time, whatever their device is set to (brief, rule 8).

- **Storage:** PostgreSQL stores `timestamptz` (UTC), with Django `USE_TZ=True` and `TIME_ZONE="Asia/Qatar"`.
- **API input:** the API accepts only ISO-8601 datetimes that carry a UTC offset. A naive time like `10:00` is ambiguous, so it is refused with `400`. Times must be whole minutes; seconds are refused.
- **API output:** the API returns times in Doha time (`+03:00`).
- **Frontend:** the frontend formats and builds times explicitly in the `Asia/Qatar` zone and never relies on the browser's own timezone.

We use the zone name everywhere, never a hard-coded `+03:00` offset. Qatar has no daylight saving today, but the zone name stays correct regardless and states the intent.

A **Day** (`?room=<id>&date=YYYY-MM-DD`) is Doha midnight to the next Doha midnight. The query returns every active booking whose slot overlaps that window (`start_time < day_end AND end_time > day_start`), so a booking from 22:00 to 01:00 appears on both days. There are no office hours, so bookings may cross midnight.

## Consequences

- The frontend must never pass a `Date` through the browser's local zone when building a request.
- Tests cover a booking that crosses midnight appearing on both Days, a Day boundary computed in Doha time and not UTC, and a refused offset-less timestamp.
