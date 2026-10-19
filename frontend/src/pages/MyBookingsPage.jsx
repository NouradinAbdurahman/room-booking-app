import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../api/index.js";
import CancelBookingButton from "../components/CancelBookingButton.jsx";
import { AlertIcon } from "../components/Icons.jsx";
import NoticeBanner from "../components/NoticeBanner.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { dohaDateOf, formatDohaDate, formatDohaTime } from "../utils/dohaTime.js";

/** The User's own Upcoming bookings across every Room and Day (visual 8, panel 5). */
export default function MyBookingsPage() {
  const [bookings, setBookings] = useState(null);
  const [loadError, setLoadError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [reloads, setReloads] = useState(0);

  useEffect(() => {
    let ignore = false; // set on unmount so a late response is dropped
    api
      .listAll("/api/bookings/?mine=true")
      .then((list) => {
        if (ignore) return;
        setBookings(list);
        setLoadError(null);
      })
      .catch((err) => {
        if (ignore) return;
        setBookings(null); // never show a stale list under the error
        setLoadError(err.message);
      });
    return () => {
      ignore = true;
    };
  }, [reloads]);

  function handleCancelled() {
    setNotice({ kind: "success", text: "Booking cancelled." });
    setReloads((n) => n + 1);
  }

  function handleCancelFailed(err) {
    setNotice({ kind: "error", text: err.message });
    setReloads((n) => n + 1); // e.g. already cancelled elsewhere: show the current list
  }

  return (
    <>
      <PageHeader title="My Bookings" subtitle="Manage your upcoming bookings" />

      <NoticeBanner notice={notice} />
      {loadError && (
        <div className="banner banner--error" role="alert">
          <AlertIcon /> {loadError}
        </div>
      )}
      {!bookings && !loadError && (
        <p className="muted" role="status">
          Loading your bookings…
        </p>
      )}
      {bookings?.length === 0 && (
        <p className="muted">
          You have no upcoming bookings. <Link to="/rooms">Book a room</Link>
        </p>
      )}

      {bookings?.length > 0 && (
        <div className="table-scroll">
          <table className="bookings-table">
            <thead>
              <tr>
                <th scope="col">Room</th>
                <th scope="col">Title</th>
                <th scope="col">Date</th>
                <th scope="col">Time</th>
                <th scope="col" className="bookings-table__action">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {bookings.map((booking) => (
                <tr key={booking.id}>
                  <td>
                    <Link to={`/rooms/${booking.room.id}?date=${dohaDateOf(booking.start_time)}`}>
                      {booking.room.name}
                    </Link>
                  </td>
                  <td>{booking.title}</td>
                  <td>{formatDohaDate(booking.start_time)}</td>
                  <td>
                    {formatDohaTime(booking.start_time)} – {formatDohaTime(booking.end_time)}
                    {endsOnALaterDay(booking) && <span className="muted"> (next day)</span>}
                  </td>
                  <td className="bookings-table__action">
                    <CancelBookingButton booking={booking} onCancelled={handleCancelled} onFailed={handleCancelFailed} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function endsOnALaterDay(booking) {
  return dohaDateOf(booking.end_time) !== dohaDateOf(booking.start_time);
}
