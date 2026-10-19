# 03: Doha time module (frontend)

**What to build:** One frontend module owns all date and time logic, so every screen shows and accepts Doha time, whatever the User's device is set to (brief rule 8; spec §5; ADR 0005; visual 5).

**Blocked by:** 01

**Status:** done

- [ ] The module formats a UTC instant as a Doha date and time, using `Intl` with `timeZone: 'Asia/Qatar'`.
- [ ] It builds an offset-aware ISO-8601 string (whole minutes) from a Doha date and time the User picked, without going through the browser's local timezone.
- [ ] It gives "today" as a Doha calendar date.
- [ ] It gives a Day's start and end instants for a Doha date.
- [ ] It gives the duration between two picked times.
- [ ] It clips a Booking that crosses midnight to a Day's edges for display, while keeping the real times available.
- [ ] Logic always uses the zone name `Asia/Qatar`, never a hard-coded `+03:00` offset.
- [ ] Vitest runs with `TZ=America/New_York` and covers each function, including:
  - a UTC instant just before midnight UTC that is already the next day in Doha;
  - a Booking from 22:00 to 01:00;
  - building an ISO string that comes out the same whatever the process timezone is.
