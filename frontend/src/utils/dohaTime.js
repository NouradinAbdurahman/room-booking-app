// All date and time logic for the app. The office runs on Doha time, so every
// value is computed in the Asia/Qatar zone and never in the browser's own zone
// (ADR 0005). The zone is always named; no "+03:00" offset is hard-coded.

export const DOHA_TIME_ZONE = "Asia/Qatar";

const dateFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: DOHA_TIME_ZONE,
  day: "numeric",
  month: "short",
  year: "numeric",
});

const timeFormatter = new Intl.DateTimeFormat("en-GB", {
  timeZone: DOHA_TIME_ZONE,
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
});

const isoDateFormatter = new Intl.DateTimeFormat("en-CA", {
  timeZone: DOHA_TIME_ZONE,
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

/** "19 Oct 2026": the Doha calendar date of an instant (Date or ISO string). */
export function formatDohaDate(instant) {
  return dateFormatter.format(new Date(instant));
}

/** "00:30": the 24-hour Doha clock time of an instant. */
export function formatDohaTime(instant) {
  return timeFormatter.format(new Date(instant));
}

/** "2026-10-19": today's date in Doha. */
export function todayInDoha(now = new Date()) {
  return isoDateFormatter.format(now);
}

const offsetFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: DOHA_TIME_ZONE,
  timeZoneName: "longOffset",
});

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const TIME_PATTERN = /^(\d{2}):(\d{2})$/;

/**
 * "2026-10-18T10:00:00+03:00": the instant a User means by a Doha date
 * ("YYYY-MM-DD") and time ("HH:MM"), as the API expects it. Built from the
 * zone's own offset, never through the browser's local timezone.
 */
export function toDohaIso(date, time) {
  const [, year, month, day] = match(DATE_PATTERN, date, "date");
  const [, hour, minute] = match(TIME_PATTERN, time, "time");

  // Read the wall-clock fields as if they were UTC, then shift by Doha's
  // offset. A second lookup at the shifted instant keeps this correct even
  // if the zone ever changes offset (Qatar has no daylight saving today).
  const wallClockAsUtc = Date.UTC(+year, +month - 1, +day, +hour, +minute);
  const guess = offsetMinutes(new Date(wallClockAsUtc));
  const offset = offsetMinutes(new Date(wallClockAsUtc - guess * 60_000));

  return `${date}T${time}:00${formatOffset(offset)}`;
}

/** The instants where a Doha calendar Day starts and ends (exclusive). */
export function dohaDayBounds(date) {
  return {
    start: new Date(toDohaIso(date, "00:00")),
    end: new Date(toDohaIso(addDays(date, 1), "00:00")),
  };
}

/** Calendar arithmetic on "YYYY-MM-DD" strings, free of any timezone. */
export function addDays(date, days) {
  const [, year, month, day] = match(DATE_PATTERN, date, "date");
  return new Date(Date.UTC(+year, +month - 1, +day + days)).toISOString().slice(0, 10);
}

function offsetMinutes(instant) {
  const name = offsetFormatter.formatToParts(instant).find((p) => p.type === "timeZoneName").value;
  const parsed = /^GMT(?:([+-])(\d{2}):(\d{2}))?$/.exec(name);
  if (!parsed[1]) return 0;
  const minutes = Number(parsed[2]) * 60 + Number(parsed[3]);
  return parsed[1] === "-" ? -minutes : minutes;
}

function formatOffset(minutes) {
  const sign = minutes < 0 ? "-" : "+";
  const abs = Math.abs(minutes);
  return `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function match(pattern, value, label) {
  const result = pattern.exec(value);
  if (!result) throw new Error(`Invalid ${label}: ${value}`);
  return result;
}

/** Whole minutes between two instants (Date or ISO string). */
export function durationMinutes(start, end) {
  return Math.round((new Date(end) - new Date(start)) / 60_000);
}

/**
 * The part of a Booking that falls on a Doha Day, for drawing it on that
 * Day's schedule. The Booking's real times are untouched; the flags say
 * whether it continues from the previous Day or into the next one.
 */
export function clipToDay({ start, end }, date) {
  const day = dohaDayBounds(date);
  const bookingStart = new Date(start);
  const bookingEnd = new Date(end);

  return {
    start: bookingStart < day.start ? day.start : bookingStart,
    end: bookingEnd > day.end ? day.end : bookingEnd,
    startsBeforeDay: bookingStart < day.start,
    endsAfterDay: bookingEnd > day.end,
  };
}
