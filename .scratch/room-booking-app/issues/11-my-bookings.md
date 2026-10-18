# 11: My Bookings

**What to build:** A User opens My Bookings and sees all their Upcoming bookings across every Room and Day, and can Cancel any of them. They never see anyone else's (spec §4, §6; ADRs 0005, 0006; visual 8 panel 5).

**Blocked by:** 10

**Status:** ready-for-agent

- [ ] `GET /api/bookings/?mine=true` returns paginated Active bookings of the **session** User with `end_time > now`, ordered by `start_time`. The User always comes from the session. Combining `mine` with `room` or `date` returns `400`.
- [ ] Seam 1 tests:
  - other Users' bookings, Cancelled bookings and ended bookings are excluded;
  - 150 Upcoming bookings come back as 100 + 50 over two pages, with a working `next`;
  - `page_size` above 100 is capped;
  - the query count stays the same for 5 and for 50 bookings.
- [ ] The My Bookings page matches visual 8 panel 5: a table with Room, Title, Date, Time (Doha) and Cancel. All pages are fetched by following `next`.
- [ ] Cancel uses the same in-app confirmation as ticket 10 and removes the row on success.
