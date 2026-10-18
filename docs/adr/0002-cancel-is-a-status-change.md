# Cancelling a booking keeps the row and marks it cancelled

A booking has a `status` of `active` or `cancelled`. Cancelling sets `status = 'cancelled'` and records `cancelled_at` (and `updated_at`) instead of deleting the row. The API still exposes cancellation as `DELETE /api/bookings/{id}/` returning `204 No Content`, because to the user the booking is gone. Cancelled bookings never appear in a Day's schedule or under My Bookings.

We chose this because the history of who booked and who cancelled stays answerable, and the exclusion constraint (ADR 0001) only needs a `WHERE status = 'active'` clause to free the slot. A future reader may be surprised that `DELETE` does not delete a row; this note is why.

## Consequences

- Only the Booker may cancel. Anyone else gets `403` ("You can only cancel your own bookings."). Bookings are visible to all logged-in users, so `403` hides nothing.
- The brief states only the Booker restriction, so no time rule is added: a Booker may cancel any of their active bookings, including one that has started or ended. The README states this as a deliberate reading of the brief.
- Cancelling an already-cancelled booking returns `404`, because it is no longer an active booking.
- A database CHECK keeps `cancelled_at` consistent with `status`: it is set if and only if the booking is cancelled.
