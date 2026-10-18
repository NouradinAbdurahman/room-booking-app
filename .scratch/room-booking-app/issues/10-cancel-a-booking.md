# 10: Cancel a Booking

**What to build:** A Booker cancels one of their Bookings from the Room schedule after confirming. The Slot is freed straight away for anyone to book, and the record of the Booking is kept. Nobody else can Cancel it (brief rule 7; spec §2, §4, §5; ADR 0002; visual 8 panels 3 and 6).

**Blocked by:** 08

**Status:** ready-for-agent

- [ ] `DELETE /api/bookings/{id}/`:
  - **Booker, Active booking:** one conditional update sets `status = cancelled`, `cancelled_at` and `updated_at`, and returns `204`. The row is not deleted.
  - **Another User's Booking:** `403 not_booker` ("You can only cancel your own bookings.").
  - **Unknown id or already Cancelled:** `404 not_found`.
- [ ] There is no time limit: a Booking that has started or ended can still be cancelled by its Booker.
- [ ] Seam 1 tests:
  - the Booker gets `204` and the row still exists as cancelled;
  - the same Slot can then be booked again with `201`;
  - a non-Booker gets `403`;
  - a second cancel gets `404`;
  - a Booking that has started can be cancelled.
- [ ] `PUT` and `PATCH` on a Booking return `405` in the error envelope.
- [ ] On the Room Schedule, a Cancel action appears **only** on the User's own Bookings. It asks for confirmation inside the app (never the browser's `confirm()`), then refreshes the schedule and shows a success or error banner.
