import { useEffect, useRef, useState } from "react";
import { api } from "../api/index.js";
import {
  durationMinutes,
  formatDohaTime,
  formatDuration,
  nextQuarterHour,
  toDohaIso,
  todayInDoha,
} from "../utils/dohaTime.js";
import { AlertIcon, ClockIcon, XIcon } from "./Icons.jsx";
import RoomSummary from "./RoomSummary.jsx";

const MIN_MINUTES = 15;
const MAX_MINUTES = 4 * 60;
const LIMITS = "Must be between 15 minutes and 4 hours";

/**
 * Book the Room being viewed (visual 8, panel 4). Times are picked as Doha
 * dates and times; the server decides every rule and its message is shown.
 */
export default function CreateBookingDialog({ room, date, onClose, onCreated }) {
  const [form, setForm] = useState(() => defaultForm(date));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [fieldErrors, setFieldErrors] = useState({});
  const titleInput = useRef(null);

  useEffect(() => {
    titleInput.current?.focus();
    const closeOnEscape = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", closeOnEscape);
    return () => window.removeEventListener("keydown", closeOnEscape);
  }, [onClose]);

  const times = isoTimes(form);
  const minutes = times ? durationMinutes(times.start, times.end) : null;

  // Editing the form clears the last answer, so an old refusal never sits next to new values.
  const update = (field) => (event) => {
    setForm((current) => ({ ...current, [field]: event.target.value }));
    setError(null);
    setFieldErrors({});
  };

  async function handleSubmit(event) {
    event.preventDefault();
    if (!times) {
      setError("Enter a valid start and end date and time.");
      return;
    }
    setSubmitting(true);
    setError(null);
    setFieldErrors({});
    try {
      const booking = await api.post("/api/bookings/", {
        room_id: room.id,
        title: form.title,
        start_time: times.start,
        end_time: times.end,
      });
      onCreated(booking);
    } catch (err) {
      setError(err.message);
      setFieldErrors(err.fields ?? {});
      setSubmitting(false);
    }
  }

  return (
    <div className="dialog-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="create-booking-title"
        onSubmit={handleSubmit}
        noValidate
      >
        <header className="dialog__header">
          <h2 id="create-booking-title">Book {room.name}</h2>
          <button type="button" className="dialog__close" aria-label="Close" onClick={onClose}>
            <XIcon />
          </button>
        </header>

        <div className="dialog__room">
          <RoomSummary room={room} />
        </div>

        <label className="field">
          <span>Meeting title</span>
          <input ref={titleInput} value={form.title} onChange={update("title")} maxLength={200} required />
          <FieldError messages={fieldErrors.title} />
        </label>

        <fieldset className="field">
          <legend>Start time</legend>
          <div className="field__pair">
            <input type="date" aria-label="Start date" value={form.startDate} onChange={update("startDate")} required />
            <input type="time" aria-label="Start time" step={900} value={form.startTime} onChange={update("startTime")} required />
          </div>
          <FieldError messages={fieldErrors.start_time} />
        </fieldset>

        <fieldset className="field">
          <legend>End time</legend>
          <div className="field__pair">
            <input type="date" aria-label="End date" value={form.endDate} onChange={update("endDate")} required />
            <input type="time" aria-label="End time" step={900} value={form.endTime} onChange={update("endTime")} required />
          </div>
          <FieldError messages={fieldErrors.end_time} />
        </fieldset>

        <DurationHint minutes={minutes} />

        {error && (
          <div className="banner banner--error" role="alert">
            <AlertIcon /> {error}
          </div>
        )}

        <div className="dialog__actions">
          <button type="button" className="button button--secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="button button--primary" disabled={submitting}>
            {submitting ? "Booking…" : "Book"}
          </button>
        </div>
      </form>
    </div>
  );
}

function DurationHint({ minutes }) {
  if (minutes === null) {
    return <p className="duration duration--warning">Choose a start and end date and time.</p>;
  }
  if (minutes <= 0) {
    return (
      <p className="duration duration--warning">
        <ClockIcon /> End time must be after the start time.
      </p>
    );
  }
  const outside = minutes < MIN_MINUTES || minutes > MAX_MINUTES;
  return (
    <p className={`duration${outside ? " duration--warning" : ""}`}>
      <ClockIcon />
      <span>
        <strong>Duration: {formatDuration(minutes)}</strong>
        <span>({LIMITS})</span>
      </span>
    </p>
  );
}

function FieldError({ messages }) {
  return messages?.length ? <span className="field__error">{messages.join(" ")}</span> : null;
}

/** Start on the viewed Day: the next quarter hour if it is today, otherwise 09:00; one hour long. */
function defaultForm(date) {
  const now = new Date();
  const start = date === todayInDoha(now) ? nextQuarterHour(now) : new Date(toDohaIso(date, "09:00"));
  const end = new Date(start.getTime() + 60 * 60_000);
  return {
    title: "",
    startDate: todayInDoha(start),
    startTime: formatDohaTime(start),
    endDate: todayInDoha(end),
    endTime: formatDohaTime(end),
  };
}

/** The picked Doha date/times as API times, or null while any of them is incomplete. */
function isoTimes(form) {
  try {
    return { start: toDohaIso(form.startDate, form.startTime), end: toDohaIso(form.endDate, form.endTime) };
  } catch {
    return null;
  }
}
