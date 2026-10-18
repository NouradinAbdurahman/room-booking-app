# Room Booking

Booking meeting rooms in the Doha office so that no room is ever double-booked.

## Language

### People

**User**:
A person with a demo account who can log in. There is no self sign-up.
_Avoid_: Account, member, customer

**Booker**:
The User who made a particular Booking. Only the Booker may cancel it.
_Avoid_: Owner, creator, created by, organiser, host

### Rooms and bookings

**Room**:
A meeting room in the Doha office, identified by a name and having a capacity.
_Avoid_: Space, resource, venue

**Capacity**:
The number of people a Room holds. It is informational only and does not restrict who can book.
_Avoid_: Size, seats

**Booking**:
One Room reserved by one Booker for one continuous period, with a title.
_Avoid_: Reservation, meeting, event, appointment

**Slot**:
The period a Booking occupies, from its start up to (but not including) its end. Two Slots that only touch, one ending at 10:00 and the next starting at 10:00, do not overlap.
_Avoid_: Time range, window, period

**Active booking**:
A Booking that has not been cancelled. Only Active bookings occupy their Slot.
_Avoid_: Confirmed booking, live booking

**Cancelled booking**:
A Booking that its Booker has withdrawn. It no longer occupies its Slot, so the Slot can be booked again, but the record of it is kept.
_Avoid_: Deleted booking, removed booking

**Upcoming booking**:
An Active booking that has not yet ended. A User's own Upcoming bookings are what they see under "My Bookings".
_Avoid_: Future booking, pending booking

**Cancel**:
What a Booker does to turn their Active booking into a Cancelled booking.
_Avoid_: Delete, remove, release

### Rules and outcomes

**Double-booking**:
Two Active bookings for the same Room whose Slots overlap. It must never exist.
_Avoid_: Clash, collision, overbooking

**Conflict**:
The reason a new Booking is refused because its Slot overlaps an existing Active booking in the same Room.
_Avoid_: Clash, collision

**Refusal**:
A Booking request that is rejected, always together with a clear reason the User can read.
_Avoid_: Error, failure, rejection

### Time

**Doha time**:
The office's local time (Asia/Qatar). It is the only time Users ever see or enter, whatever their own device is set to.
_Avoid_: Local time, browser time, server time

**Day**:
One calendar day in Doha time, from midnight to midnight. A Day's schedule for a Room includes every Booking whose Slot overlaps that Day, including Bookings that cross midnight.
_Avoid_: Date (when the whole day is meant), 24 hours
