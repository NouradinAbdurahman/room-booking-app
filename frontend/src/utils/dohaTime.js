// All date and time logic for the app. The office runs on Doha time, so every
// value is computed in the Asia/Qatar zone and never in the browser's own zone
// (ADR 0005). The zone is always named; no "+03:00" offset is hard-coded.

export const DOHA_TIME_ZONE = "Asia/Qatar";

// Month labels are fixed here rather than taken from Intl, because some ICU
// versions print "Sept" where the design (and older engines) say "Sep".
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

const DATE_PATTERN = /^(\d{4})-(\d{2})-(\d{2})$/;
const TIME_PATTERN = /^([01]\d|2[0-3]):([0-5]\d)$/;

const dohaFieldsFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: DOHA_TIME_ZONE,
  year: "numeric",
  month: "numeric",
  day: "numeric",
  hour: "numeric",
  minute: "numeric",
  hourCycle: "h23",
});

const offsetFormatter = new Intl.DateTimeFormat("en-US", {
  timeZone: DOHA_TIME_ZONE,
  timeZoneName: "longOffset",
});

/** "19 Oct 2026": the Doha calendar date of an instant (Date or ISO string). */
export function formatDohaDate(instant) {
  const { year, month, day } = dohaFields(instant);
  return `${day} ${MONTHS[month - 1]} ${year}`;
}

/** "00:30": the 24-hour Doha clock time of an instant. */
export function formatDohaTime(instant) {
  const { hour, minute } = dohaFields(instant);
  return `${pad(hour)}:${pad(minute)}`;
}

/** "2026-10-19": today's date in Doha. */
export function todayInDoha(now = new Date()) {
  const { year, month, day } = dohaFields(now);
  return `${year}-${pad(month)}-${pad(day)}`;
}

/**
 * "2026-10-18T10:00:00+03:00": the instant a User means by a Doha date
 * ("YYYY-MM-DD") and time ("HH:MM"), as the API expects it. Built from the
 * zone's own offset, never through the browser's local timezone.
 */
export function toDohaIso(date, time) {
  const { year, month, day } = parseDate(date);
  const [, hour, minute] = match(TIME_PATTERN, time, "time");

  // Read the wall-clock fields as if they were UTC, then shift by Doha's
  // offset. A second lookup at the shifted instant keeps this correct even
  // if the zone ever changes offset (Qatar has no daylight saving today).
  const wallClockAsUtc = Date.UTC(year, month - 1, day, +hour, +minute);
  const approxOffset = offsetMinutes(new Date(wallClockAsUtc));
  const offset = offsetMinutes(new Date(wallClockAsUtc - approxOffset * 60_000));

  return `${date}T${time}:00${formatOffset(offset)}`;
}

/** True for a real calendar date written exactly as "YYYY-MM-DD". */
export function isDohaDate(value) {
  try {
    parseDate(value ?? "");
    return true;
  } catch {
    return false;
  }
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
  const { year, month, day } = parseDate(date);
  return new Date(Date.UTC(year, month - 1, day + days)).toISOString().slice(0, 10);
}

/** Whole minutes between two instants (Date or ISO string). */
export function durationMinutes(start, end) {
  return Math.round((new Date(end) - new Date(start)) / 60_000);
}

const QUARTER_HOUR_MS = 15 * 60_000;

/**
 * The first quarter hour strictly after `now`. Doha's offset is a whole number
 * of quarter hours, so rounding the instant rounds the Doha clock too.
 */
export function nextQuarterHour(now = new Date()) {
  return new Date((Math.floor(now.getTime() / QUARTER_HOUR_MS) + 1) * QUARTER_HOUR_MS);
}

/** "1 hour 30 minutes": a whole-minute duration in words. */
export function formatDuration(minutes) {
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  const parts = [];
  if (hours) parts.push(`${hours} ${hours === 1 ? "hour" : "hours"}`);
  if (rest || !hours) parts.push(`${rest} ${rest === 1 ? "minute" : "minutes"}`);
  return parts.join(" ");
}

/**
 * The part of a Booking's Slot that falls on a Doha Day, for drawing it on
 * that Day's schedule. The real times are untouched; the flags say whether
 * the Slot continues from the previous Day or into the next one. Assumes the
 * Slot overlaps the Day, which the API's Day filter guarantees.
 */
export function clipToDay(slot, date) {
  const day = dohaDayBounds(date);
  const start = new Date(slot.start);
  const end = new Date(slot.end);

  return {
    start: start < day.start ? day.start : start,
    end: end > day.end ? day.end : end,
    startsBeforeDay: start < day.start,
    endsAfterDay: end > day.end,
  };
}

/**
 * A Doha Day as a list to draw: each Booking (clipped to the Day) and an
 * "available" item for every gap, from midnight to midnight. `bookings` are
 * the API's Day schedule, already ordered by start_time; the API also
 * guarantees each one overlaps the Day.
 */
export function daySchedule(bookings, date) {
  const day = dohaDayBounds(date);
  const items = [];
  let cursor = day.start;

  for (const booking of bookings) {
    const clipped = clipToDay({ start: booking.start_time, end: booking.end_time }, date);
    if (clipped.start > cursor) items.push({ kind: "available", start: cursor, end: clipped.start });
    items.push({ kind: "booking", booking, ...clipped });
    if (clipped.end > cursor) cursor = clipped.end;
  }
  if (cursor < day.end) items.push({ kind: "available", start: cursor, end: day.end });

  return items;
}

function dohaFields(instant) {
  const fields = {};
  for (const { type, value } of dohaFieldsFormatter.formatToParts(new Date(instant))) {
    if (type !== "literal") fields[type] = Number(value);
  }
  return fields;
}

function parseDate(date) {
  const [, year, month, day] = match(DATE_PATTERN, date, "date").map(Number);
  // Reject dates like 2026-02-30 that Date.UTC would silently roll over.
  const roundTrip = new Date(Date.UTC(year, month - 1, day));
  if (roundTrip.getUTCMonth() !== month - 1 || roundTrip.getUTCDate() !== day) {
    throw new Error(`Invalid date: ${date}`);
  }
  return { year, month, day };
}

function offsetMinutes(instant) {
  const name = offsetFormatter.formatToParts(instant).find((p) => p.type === "timeZoneName").value;
  const parsed = /^GMT(?:([+-])(\d{2}):(\d{2}))?$/.exec(name);
  if (!parsed) throw new Error(`Unexpected ${DOHA_TIME_ZONE} offset: ${name}`);
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
