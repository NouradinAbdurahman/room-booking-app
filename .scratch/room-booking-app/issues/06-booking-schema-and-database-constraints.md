# 06: Booking schema and database constraints

**What to build:** The database alone makes invalid Bookings and Double-bookings impossible, even for code that skips validation. This is built and proven **before** any API validation depends on it (brief rules 4, 5, 7 and "database design"; spec §2; ADRs 0001, 0002, 0003; visuals 3 and 4, with the changes listed in `docs/design/README.md`).

**Blocked by:** 05

**Status:** ready-for-agent

- [ ] The Booking model has:

  | Field | Rule |
  | --- | --- |
  | `room` | FK, protect on delete |
  | `user` | FK, the Booker; protect on delete |
  | `title` | max 200 |
  | `start_time`, `end_time` | `timestamptz` |
  | `status` | `active` or `cancelled`, default `active` |
  | `cancelled_at` | nullable |
  | `created_at`, `updated_at` | |

- [ ] A migration operation creates the `btree_gist` extension before the constraint that needs it.
- [ ] CHECK constraints: `end_time > start_time`; duration between 15 minutes and 4 hours inclusive; title not blank after trimming; `status` is one of the two values; `cancelled_at` is set if and only if `status` is `cancelled`.
- [ ] Exclusion constraint `no_overlapping_active_bookings` using GiST: room equality and `tstzrange(start_time, end_time, '[)')` overlap, `WHERE status = 'active'`.
- [ ] Partial btree indexes for active bookings on `(room_id, start_time)` and `(user_id, start_time)`.
- [ ] Seam 2 tests, writing through the ORM with no validation, show that PostgreSQL **rejects**:
  - an overlapping Active booking in the same Room;
  - 14 minutes, and 4 hours plus 1 minute;
  - end ≤ start;
  - a blank title;
  - a cancelled status with no `cancelled_at`, and the reverse.
- [ ] Seam 2 tests show PostgreSQL **accepts**:
  - exactly 15 minutes and exactly 4 hours;
  - touching Slots (one ending at 10:00, the next starting at 10:00);
  - an overlapping *cancelled* booking;
  - an overlap in a different Room.
- [ ] A catalog test confirms `no_overlapping_active_bookings` exists with its active-only condition on PostgreSQL 17.
- [ ] The `sqlmigrate` output and `\d` on the bookings table are captured for the README.
