# 09: Simultaneous-booking proof

**What to build:** Automated proof that when two Users book the same Slot at the same moment, exactly one succeeds and the Room is never double-booked (brief rule 6; spec Testing Decisions › Concurrency; ADR 0001; visual 4 panel 4).

**Blocked by:** 08

**Status:** done

- [ ] A transactional test on real PostgreSQL. It never uses SQLite or test-wrapping transactions that would hide the race.
- [ ] Two threads, each with its own client and logged-in User (CSRF handled), wait at a barrier and then both `POST` the same Room and Slot.
- [ ] Exactly one response is `201`, the other is `409 booking_conflict`, and exactly one Active booking exists for that Slot.
- [ ] The test repeats several times in one run to reduce the chance of the race being missed by luck. It cleans up its data and closes database connections in each thread.
- [ ] The test lives in the normal suite and passes with `docker compose run --rm backend pytest`.
