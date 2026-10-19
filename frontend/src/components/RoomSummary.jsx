import { UsersIcon } from "./Icons.jsx";

export function capacityLabel(capacity) {
  return `Capacity: ${capacity} ${capacity === 1 ? "person" : "people"}`;
}

/** A Room's icon, name and Capacity, as on the room cards and schedule header (visual 8). */
export default function RoomSummary({ room, heading = false }) {
  const Name = heading ? "h1" : "strong";
  return (
    <>
      <span className="room-card__icon">
        <UsersIcon />
      </span>
      <span className="room-card__text">
        <Name>{room.name}</Name>
        <span className="muted">{capacityLabel(room.capacity)}</span>
      </span>
    </>
  );
}
