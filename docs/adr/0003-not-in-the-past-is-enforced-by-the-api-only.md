# "Cannot start in the past" is enforced by the API, not by a database constraint

The brief asks for database constraints so that invalid data cannot be saved even by code that skips validation. Most booking rules are database CHECK constraints:

- end is after start
- duration is between 15 minutes and 4 hours
- the title is not blank
- room capacity is positive
- room names are unique
- `cancelled_at` is set if and only if the status is cancelled (ADR 0002)

The exception is "a booking cannot start in the past". PostgreSQL requires CHECK constraints to give the same answer forever, and a rule based on `now()` does not. A booking that was valid when created would become "invalid" once its start time passes, which would break backups, restores and any later update to the row. So this rule lives in the API serializer, which compares against the server clock at request time.

## Consequences

- The server's clock is the authority. The frontend's clock is never trusted.
- The README calls out this rule as the one rule the database cannot enforce, and explains why.
