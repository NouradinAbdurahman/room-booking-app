# 05: Rooms: model, constraints, list API, Rooms page

**What to build:** A logged-in User sees the list of Rooms with their name and Capacity and can open one. The database itself rejects duplicate Room names and Capacities that aren't positive (brief rule 2; spec §2, §4, §6; ADR 0003; visual 3, visual 8 panel 2).

**Blocked by:** 04

**Status:** ready-for-agent

- [ ] The Room model has `name` (unique, not blank), `capacity` (positive), `created_at` and `updated_at`. The constraints are declared on the model and appear in the migration.
- [ ] Seam 2 tests, writing straight through the ORM without validation, show that a duplicate name and a capacity of 0 or less are rejected by PostgreSQL.
- [ ] The idempotent demo seed adds "Conference Room A" (10), "Meeting Room B" (6) and "Focus Room" (4).
- [ ] `GET /api/rooms/` requires a logged-in User and returns paginated Rooms ordered by name, shaped as `{"count", "next", "previous", "results": [{"id", "name", "capacity"}]}`. `page_size` defaults to and is capped at 100.
- [ ] The Rooms page matches visual 8 panel 2: room cards with an icon, the name and "Capacity: N people", each linking to that Room's schedule route. Room photos from visual 1 are not used.
- [ ] Seam 1 tests: logged out gives `401`; the list shape and order are correct; asking for `page_size` above 100 is capped.
