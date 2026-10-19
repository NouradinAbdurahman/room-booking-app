# 07: A Room's Day schedule

**What to build:** A User opens a Room and sees every Active booking that overlaps the chosen Doha Day, including Bookings that cross midnight. They can step between Days, and the screen stays fast on busy Days (brief rules 8 and 10; spec §4, §5, §6; ADRs 0005, 0006; visual 8 panel 3).

**Blocked by:** 03, 06

**Status:** done

- [ ] `GET /api/bookings/?room=<id>&date=YYYY-MM-DD` returns paginated Active bookings with `start_time < day_end AND end_time > day_start`. The Day is computed in `Asia/Qatar`. Results are ordered by `start_time`.
- [ ] Booking shape: `{"id", "room": {"id", "name", "capacity"}, "title", "start_time", "end_time", "booked_by": {"id", "username"}, "created_at"}`. Times are in `+03:00`.
- [ ] Filter checking: exactly one filter form. A missing or partial `room`/`date`, an invalid date, or an unknown room returns `400 validation_error` with field messages. (The `mine` form arrives in ticket 11. Until then, `mine` returns `400`.)
- [ ] Seam 1 tests, with Bookings created through the ORM:
  - a 22:00–01:00 Booking appears on both Days;
  - a 00:30 Doha Booking appears on its Doha date even though it is the previous date in UTC;
  - Cancelled bookings and other Rooms are excluded;
  - results are ordered;
  - a small `page_size` returns every overlapping Booking exactly once across all pages;
  - the query count stays the same for 5 and for 50 Bookings.
- [ ] The Room Schedule screen matches visual 8 panel 3:
  - "Back to Rooms", the Room name and Capacity;
  - a date stepper (previous, picker, next) that defaults to today in Doha, with the date reflected in the URL;
  - booking blocks showing title, Doha times and Booker;
  - "Available" placeholders for gaps;
  - a "Book This Room" button, which ticket 08 wires up.

  All times go through the Doha time module.
