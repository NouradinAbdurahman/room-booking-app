import { useEffect, useState } from "react";
import { Link } from "react-router";
import { api } from "../api/index.js";
import { AlertIcon, ChevronRightIcon, UsersIcon } from "../components/Icons.jsx";
import PageHeader from "../components/PageHeader.jsx";

/** Every Room as a card linking to its schedule (visual 8, panel 2). */
export default function RoomsPage() {
  const [rooms, setRooms] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let ignore = false; // set on unmount so a late response is dropped
    api
      .listAll("/api/rooms/")
      .then((list) => !ignore && setRooms(list))
      .catch((err) => !ignore && setError(err.message));
    return () => {
      ignore = true;
    };
  }, []);

  return (
    <>
      <PageHeader title="Meeting Rooms" subtitle="Select a room to view its schedule and book" />

      {error && (
        <div className="banner banner--error" role="alert">
          <AlertIcon /> {error}
        </div>
      )}
      {!rooms && !error && <p className="muted">Loading rooms…</p>}
      {rooms?.length === 0 && <p className="muted">No rooms yet.</p>}

      {rooms?.length > 0 && (
        <ul className="room-list">
          {rooms.map((room) => (
            <li key={room.id}>
              <Link to={`/rooms/${room.id}`} className="room-card">
                <span className="room-card__icon">
                  <UsersIcon />
                </span>
                <span className="room-card__text">
                  <strong>{room.name}</strong>
                  <span className="muted">
                    Capacity: {room.capacity} {room.capacity === 1 ? "person" : "people"}
                  </span>
                </span>
                <ChevronRightIcon className="room-card__chevron" />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </>
  );
}
