import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router";
import { api } from "../api/index.js";
import DateStepper from "../components/DateStepper.jsx";
import { AlertIcon, ArrowLeftIcon, PlusIcon } from "../components/Icons.jsx";
import RoomSummary from "../components/RoomSummary.jsx";
import { daySchedule, formatDohaTime, isDohaDate, todayInDoha } from "../utils/dohaTime.js";

const BOOKING_COLOURS = ["blue", "green", "purple"];

/** A Room's schedule for one Doha Day (visual 8, panel 3). */
export default function RoomSchedulePage() {
  const { roomId } = useParams();
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedDate = searchParams.get("date");
  const date = isDohaDate(requestedDate) ? requestedDate : todayInDoha();

  // The selected Day always lives in the URL: a missing or invalid ?date=
  // is replaced with today, without adding a history entry.
  useEffect(() => {
    if (requestedDate !== date) setSearchParams({ date }, { replace: true });
  }, [requestedDate, date, setSearchParams]);

  const [room, setRoom] = useState(null);
  // Each result remembers the request it answers, so a response for another
  // Room or Day is never drawn, and a past error never lingers.
  const [schedule, setSchedule] = useState(null);

  useEffect(() => {
    let ignore = false; // set on unmount so a late response is dropped
    setRoom(null);
    api
      .listAll("/api/rooms/")
      .then((rooms) => {
        if (ignore) return;
        const found = rooms.find((r) => String(r.id) === roomId);
        setRoom(found ? { roomId, room: found } : { roomId, error: "This room does not exist." });
      })
      .catch((err) => !ignore && setRoom({ roomId, error: err.message }));
    return () => {
      ignore = true;
    };
  }, [roomId]);

  useEffect(() => {
    let ignore = false;
    const query = new URLSearchParams({ room: roomId, date });
    api
      .listAll(`/api/bookings/?${query}`)
      .then((bookings) => !ignore && setSchedule({ roomId, date, bookings }))
      .catch((err) => !ignore && setSchedule({ roomId, date, error: err.message }));
    return () => {
      ignore = true;
    };
  }, [roomId, date]);

  const current = (result) => result?.roomId === roomId && (result.date ?? date) === date;
  const roomResult = current(room) ? room : null;
  const scheduleResult = current(schedule) ? schedule : null;
  // An unknown Room fails both requests; show only the Room's message.
  const error = roomResult?.error ?? scheduleResult?.error;

  return (
    <div className="schedule">
      <Link to="/rooms" className="back-link">
        <ArrowLeftIcon width={16} height={16} /> Back to Rooms
      </Link>

      {roomResult?.room && (
        <header className="schedule__header">
          <RoomSummary room={roomResult.room} heading />
        </header>
      )}

      {error ? (
        <div className="banner banner--error" role="alert">
          <AlertIcon /> {error}
        </div>
      ) : (
        <>
          <DateStepper date={date} onChange={(next) => setSearchParams({ date: next })} />
          {scheduleResult?.bookings ? (
            <Timeline items={daySchedule(scheduleResult.bookings, date)} />
          ) : (
            <p className="muted">Loading schedule…</p>
          )}
          {/* Booking a Room arrives in ticket 08. */}
          <button type="button" className="button button--primary button--block" disabled>
            <PlusIcon /> Book This Room
          </button>
        </>
      )}
    </div>
  );
}

function Timeline({ items }) {
  const bookings = items.filter((item) => item.kind === "booking");
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
            <div className="timeline__block timeline__block--available">Available</div>
          ) : (
            <BookingBlock item={item} colour={BOOKING_COLOURS[bookings.indexOf(item) % BOOKING_COLOURS.length]} />
          )}
        </li>
      ))}
    </ol>
  );
}

function BookingBlock({ item, colour }) {
  const { booking, startsBeforeDay, endsAfterDay } = item;
  return (
    <div className={`timeline__block timeline__block--booking timeline__block--${colour}`}>
      <strong>{booking.title}</strong>
      <span>
        {formatDohaTime(booking.start_time)} – {formatDohaTime(booking.end_time)}
        {startsBeforeDay && <em> (from the previous day)</em>}
        {endsAfterDay && <em> (until the next day)</em>}
      </span>
      <span className="timeline__booker">{booking.booked_by.username}</span>
    </div>
  );
}
