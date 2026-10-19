# The database, not the application, prevents double-booking

A room must never be double-booked, even when two people book the same slot at the same moment (brief, rules 5 and 6). We enforce this with a PostgreSQL exclusion constraint on the bookings table:

```sql
CREATE EXTENSION IF NOT EXISTS btree_gist;

ALTER TABLE bookings ADD CONSTRAINT no_overlapping_active_bookings
  EXCLUDE USING gist (
    room_id WITH =,
    tstzrange(start_time, end_time, '[)') WITH &&
  ) WHERE (status = 'active');
```

`btree_gist` lets room equality and range overlap share one GiST index. The ranges are half-open (`[)`), so a booking ending at 10:00 and one starting at 10:00 do not overlap. The `WHERE` clause limits the rule to active bookings, so cancelling a booking frees its slot without deleting its record (ADR 0002).

The application still checks for overlap before inserting, but only to give a readable refusal message. Correctness never depends on that check: two simultaneous requests can both pass it. The database then accepts one insert and rejects the other.

## Considered options

- **Application-level check only.** Rejected. There is a race window between "check" and "insert", which is exactly the scenario in rule 6.
- **`SELECT ... FOR UPDATE` or an advisory lock per room.** Rejected. Every code path must remember to take the lock, and all bookings for a room are serialised even when they don't overlap. The constraint also protects writes that bypass the API.
- **A `SERIALIZABLE` transaction with retries.** Rejected. It is correct, but it needs retry logic and is harder to explain and test than a declarative constraint.

## Consequences

- Start and end are stored as two plain `timestamptz` columns, `start_time` and `end_time`. The range exists only inside the constraint expression, which keeps the Django model and serializers simple.
- The constraint is declared in the Django model with `ExclusionConstraint`, and the extension is created with a `BtreeGistExtension` migration operation that runs before it.
- Only a PostgreSQL exclusion violation on this constraint becomes `409 Conflict`. The check is SQLSTATE `23P01` **and** the constraint name `no_overlapping_active_bookings`. Every other database error, including other integrity errors, propagates normally and is never reported as a booking conflict.
- Two truly simultaneous overlapping inserts can **deadlock** inside PostgreSQL's exclusion check: each finds the other's uncommitted row and waits for it. PostgreSQL then aborts one with SQLSTATE `40P01`. Found by the concurrency test (ticket 09).
  - The data is still correct: exactly one Booking remains.
  - Unhandled, though, the losing request would get a `500` instead of a clear refusal.
  - So the insert is retried (up to 3 attempts). The retry either meets the other, now committed, Booking (`23P01`, so `409`) or finds the Slot free (`201`).
  - A deadlock is never itself mapped to `409`, and there is still no application-level locking.
- To verify during implementation, on PostgreSQL 17 as pinned in Docker Compose (ADR 0007):
  - Inspect the SQL from `sqlmigrate`.
  - Check that `\d bookings_booking` shows the constraint with its `WHERE` clause.
  - Run a threaded test against real PostgreSQL, never SQLite, showing that exactly one of two simultaneous identical requests succeeds.
  - Run a test showing that a cancelled booking's slot can be booked again.
