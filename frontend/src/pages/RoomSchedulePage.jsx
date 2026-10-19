import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { api } from "../api/index.js";
import DateStepper from "../components/DateStepper.jsx";
import { AlertIcon, ArrowLeftIcon, PlusIcon, UsersIcon } from "../components/Icons.jsx";
import { daySchedule, dohaDayBounds, formatDohaTime, todayInDoha } from "../utils/dohaTime.js";

const BOOKING_COLOURS = ["blue", "green", "purple"];

/** A Room's schedule for one Doha Day (visual 8, panel 3). */
export default function RoomSchedulePage() {
  const { roomId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const date = validDate(searchParams.get("date")) ?? todayInDoha();

  const [room, setRoom] = useState(null);
  // The Day schedule together with the date it was fetched for, so a stale
  // list is never drawn against a newly chosen date.
  const [schedule, setSchedule] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let ignore = false; // set on unmount so a late response is dropped
    api
      .listAll("/api/rooms/")
      .then((rooms) => {
        if (ignore) return;
        const found = rooms.find((r) => String(r.id) === roomId);
        found ? setRoom(found) : setError("This room does not exist.");
      })
      .catch((err) => !ignore && setError(err.message));
    return () => {
      ignore = true;
    };
  }, [roomId]);

  useEffect(() => {
    let ignore = false;
    const query = new URLSearchParams({ room: roomId, date });
    api
      .listAll(`/api/bookings/?${query}`)
      .then((bookings) => !ignore && setSchedule({ date, bookings }))
      .catch((err) => !ignore && setError(err.message));
    return () => {
      ignore = true;
    };
  }, [roomId, date]);

  return (
    <div className="schedule">
      <Link to="/rooms" className="back-link">
        <ArrowLeftIcon width={16} height={16} /> Back to Rooms
      </Link>

      {room && (
        <header className="schedule__header">
          <span className="room-card__icon">
            <UsersIcon />
          </span>
          <span className="room-card__text">
            <h1>{room.name}</h1>
            <span className="muted">
              Capacity: {room.capacity} {room.capacity === 1 ? "person" : "people"}
            </span>
          </span>
        </header>
      )}

      <DateStepper date={date} onChange={(next) => setSearchParams({ date: next })} />

      {error && (
        <div className="banner banner--error" role="alert">
          <AlertIcon /> {error}
        </div>
      )}
      {schedule?.date === date ? (
        <Timeline items={daySchedule(schedule.bookings, date)} />
      ) : (
        !error && <p className="muted">Loading schedule…</p>
      )}

      {/* Booking a Room arrives in ticket 08. */}
      <button type="button" className="button button--primary button--block" disabled>
        <PlusIcon /> Book This Room
      </button>
    </div>
  );
}

function Timeline({ items }) {
  let bookingIndex = 0;
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li
          key={item.kind === "booking" ? `booking-${item.booking.id}` : `available-${item.start.toISOString()}`}
          className="timeline__row"
        >
          <time className="timeline__time" dateTime={item.start.toISOString()}>
            {formatDohaTime(item.start)}
          </time>
          {item.kind === "available" ? (
            <div className="slot slot--available">Available</div>
          ) : (
            <BookingBlock item={item} colour={BOOKING_COLOURS[bookingIndex++ % BOOKING_COLOURS.length]} />
          )}
        </li>
      ))}
    </ol>
  );
}

function BookingBlock({ item, colour }) {
  const { booking, startsBeforeDay, endsAfterDay } = item;
  return (
    <div className={`slot slot--booking slot--${colour}`}>
      <strong>{booking.title}</strong>
      <span>
        {formatDohaTime(booking.start_time)} – {formatDohaTime(booking.end_time)}
        {startsBeforeDay && <em> (from the previous day)</em>}
        {endsAfterDay && <em> (until the next day)</em>}
      </span>
      <span className="slot__booker">{booking.booked_by.username}</span>
    </div>
  );
}

/** The ?date= value if it is a real "YYYY-MM-DD" date, otherwise null. */
function validDate(value) {
  if (!value) return null;
  try {
    dohaDayBounds(value);
    return value;
  } catch {
    return null;
  }
}
