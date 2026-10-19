# 13: Performance evidence

**What to build:** Evidence that viewing a busy Day and listing My Bookings stay fast as data grows, and that each index earns its place (brief rule 10, "Indexing" and "Performance"; spec §2, §7; ADR 0006).

**Blocked by:** 11

**Status:** done

- [ ] A development-only management command seeds a large, realistic dataset: many Bookings across Rooms, Days and Users, including Bookings that cross midnight and Cancelled bookings. It is documented and never runs automatically.
- [ ] `EXPLAIN ANALYZE` is captured on the seeded data for the Day schedule query and the My Bookings query, as the ORM actually runs them.
- [ ] Decide on the `(room_id, start_time)` partial index for active bookings, based on the plans. If the GiST index makes it redundant, drop it in a migration; otherwise keep it. Record the reason either way.
- [ ] A short summary is ready for the README covering: the plans, which index each query uses, timings, and the query-count tests from tickets 07 and 11.
