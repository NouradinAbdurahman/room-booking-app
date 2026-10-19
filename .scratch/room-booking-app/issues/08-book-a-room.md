# 08: Book a Room

**What to build:** A User books the Room they're viewing by giving a title, a start and an end in Doha time. A valid Booking appears in the schedule straight away. Any Refusal shows a clear reason, and an overlap names the Room and the conflicting times (brief rules 3, 4, 5, 9; spec §4, §5; ADRs 0001, 0003, 0005, 0006; visual 8 panel 4, visual 5).

**Blocked by:** 07

**Status:** done

- [ ] `POST /api/bookings/` takes `{"room_id", "title", "start_time", "end_time"}`, uses the session User as the Booker, and returns `201` with the Booking.
- [ ] A booking service module owns the rules, checked in the spec's order:
  1. shape: the title is not blank and at most 200 characters; times are ISO-8601 **with an offset**, in whole minutes;
  2. the Room exists;
  3. end is after start;
  4. 15 minutes ≤ duration ≤ 4 hours;
  5. start ≥ now on the server clock;
  6. friendly overlap pre-check;
  7. insert in a transaction.

  Steps 1–5 fail with `400 validation_error` and field messages.
- [ ] Overlap returns `409 booking_conflict` with the message "<Room> is already booked HH:MM–HH:MM." in Doha time, or "…is already booked at that time." if the conflicting Booking can't be re-read.
- [ ] A database error counts as a Conflict **only** if SQLSTATE is `23P01` **and** the constraint is `no_overlapping_active_bookings`. Every other database error propagates unchanged, and a test proves an unrelated integrity error is not reported as `409`.
- [ ] Seam 1 Create and Overlap tests pass:
  - exactly 15 minutes and exactly 4 hours are accepted; 14 minutes and 4 hours plus 1 minute are refused;
  - end ≤ start, a start in the past, a blank title, no offset, non-zero seconds and an unknown Room are all refused;
  - an overlap returns `409` with the message;
  - touching Slots both return `201`;
  - the same Slot in another Room returns `201`;
  - a Booking crossing midnight is accepted.
- [ ] T-AUTH-2, T-AUTH-3 and T-AUTH-5 are extended to use `POST /api/bookings/` as the authenticated unsafe request:
  - after login, the rotated token gives `201`;
  - the stale pre-login token gives `403 csrf_failed`, and no Booking is created.
- [ ] The Create Booking dialog matches visual 8 panel 4: title; start date and time; end date and time (15-minute steps by default); live duration with the "15 minutes to 4 hours" hint; Cancel and Book buttons.
- [ ] Refusals show the server's `message` and field errors. On success, the dialog closes, a green success banner appears and the schedule refreshes.
