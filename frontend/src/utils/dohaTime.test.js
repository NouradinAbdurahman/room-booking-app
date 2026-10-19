import { describe, expect, it } from "vitest";
import {
  addDays,
  clipToDay,
  daySchedule,
  dohaDayBounds,
  durationMinutes,
  formatDohaDate,
  formatDohaTime,
  formatDuration,
  isDohaDate,
  nextQuarterHour,
  todayInDoha,
  toDohaIso,
} from "./dohaTime.js";

// 21:30 UTC on 18 Oct is 00:30 on 19 Oct in Doha (UTC+3) and 17:30 on 18 Oct in New York.
const LATE_EVENING_UTC = "2026-10-18T21:30:00Z";

describe("test environment", () => {
  it("runs in a timezone that is not Doha, so browser-local bugs show up", () => {
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe("America/New_York");
  });
});

describe("formatting an instant in Doha time", () => {
  it("shows the Doha calendar date, not the UTC or browser date", () => {
    expect(formatDohaDate(LATE_EVENING_UTC)).toBe("19 Oct 2026");
  });

  it("uses three-letter month names on every engine (no ICU \"Sept\")", () => {
    expect(formatDohaDate("2026-09-05T09:00:00Z")).toBe("5 Sep 2026");
  });

  it("shows the 24-hour Doha clock time", () => {
    expect(formatDohaTime(LATE_EVENING_UTC)).toBe("00:30");
    expect(formatDohaTime("2026-10-18T10:15:00+03:00")).toBe("10:15");
  });
});

describe("today in Doha", () => {
  it("is already tomorrow in Doha while it is still today in UTC and New York", () => {
    expect(todayInDoha(new Date(LATE_EVENING_UTC))).toBe("2026-10-19");
  });

  it("matches the UTC date earlier in the day", () => {
    expect(todayInDoha(new Date("2026-10-18T08:00:00Z"))).toBe("2026-10-18");
  });
});

describe("building an API time from a picked Doha date and time", () => {
  it("produces an offset-aware ISO string in whole minutes", () => {
    expect(toDohaIso("2026-10-18", "10:00")).toBe("2026-10-18T10:00:00+03:00");
  });

  it("means the same instant whatever the browser's timezone is", () => {
    // 10:00 in Doha is 07:00 UTC; New York's own clock is irrelevant.
    expect(new Date(toDohaIso("2026-10-18", "10:00")).toISOString()).toBe(
      "2026-10-18T07:00:00.000Z",
    );
  });

  it.each([
    ["2026-02-30", "10:00"],
    ["2026-13-01", "10:00"],
    ["2026-10-18", "24:00"],
    ["2026-10-18", "10:60"],
    ["18/10/2026", "10:00"],
  ])("refuses an impossible date or time (%s %s)", (date, time) => {
    expect(() => toDohaIso(date, time)).toThrow(/Invalid/);
  });

  it("handles midnight at the start of a Doha day", () => {
    expect(new Date(toDohaIso("2026-10-19", "00:00")).toISOString()).toBe(
      "2026-10-18T21:00:00.000Z",
    );
  });
});

describe("a Doha Day's edges", () => {
  it("runs from Doha midnight to the next Doha midnight", () => {
    const { start, end } = dohaDayBounds("2026-10-19");

    expect(start.toISOString()).toBe("2026-10-18T21:00:00.000Z");
    expect(end.toISOString()).toBe("2026-10-19T21:00:00.000Z");
  });
});

describe("stepping between dates", () => {
  it("crosses month and year ends", () => {
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2026-12-31", 1)).toBe("2027-01-01");
    expect(addDays("2026-03-01", -1)).toBe("2026-02-28");
  });
});

describe("duration between two picked times", () => {
  it("counts minutes", () => {
    expect(durationMinutes("2026-10-18T10:00:00+03:00", "2026-10-18T11:30:00+03:00")).toBe(90);
  });

  it("counts across midnight", () => {
    expect(durationMinutes("2026-10-18T22:00:00+03:00", "2026-10-19T01:00:00+03:00")).toBe(180);
  });
});

describe("clipping a Booking to the Day being shown", () => {
  const lateNight = { start: "2026-10-18T22:00:00+03:00", end: "2026-10-19T01:00:00+03:00" };

  it("cuts a Booking that crosses midnight at the end of its first Day", () => {
    const clipped = clipToDay(lateNight, "2026-10-18");

    expect(clipped.start.toISOString()).toBe("2026-10-18T19:00:00.000Z"); // 22:00 Doha
    expect(clipped.end.toISOString()).toBe("2026-10-18T21:00:00.000Z"); // Doha midnight
    expect(clipped.startsBeforeDay).toBe(false);
    expect(clipped.endsAfterDay).toBe(true);
  });

  it("starts the same Booking at midnight on its second Day", () => {
    const clipped = clipToDay(lateNight, "2026-10-19");

    expect(clipped.start.toISOString()).toBe("2026-10-18T21:00:00.000Z"); // Doha midnight
    expect(clipped.end.toISOString()).toBe("2026-10-18T22:00:00.000Z"); // 01:00 Doha
    expect(clipped.startsBeforeDay).toBe(true);
    expect(clipped.endsAfterDay).toBe(false);
  });

  it("leaves a Booking inside the Day untouched", () => {
    const clipped = clipToDay(
      { start: "2026-10-18T09:00:00+03:00", end: "2026-10-18T10:00:00+03:00" },
      "2026-10-18",
    );

    expect([clipped.start.toISOString(), clipped.end.toISOString()]).toEqual([
      "2026-10-18T06:00:00.000Z",
      "2026-10-18T07:00:00.000Z",
    ]);
    expect([clipped.startsBeforeDay, clipped.endsAfterDay]).toEqual([false, false]);
  });
});

describe("laying out a Day's schedule with Available gaps", () => {
  // 20 Oct 2026 in Doha runs from 2026-10-19T21:00Z to 2026-10-20T21:00Z.
  const booking = (start, end, title) => ({ start_time: start, end_time: end, title });
  const shape = (items) =>
    items.map((item) => [
      item.kind,
      item.start.toISOString(),
      item.end.toISOString(),
      item.booking?.title ?? null,
    ]);

  it("is one Available gap when the Day is empty", () => {
    expect(shape(daySchedule([], "2026-10-20"))).toEqual([
      ["available", "2026-10-19T21:00:00.000Z", "2026-10-20T21:00:00.000Z", null],
    ]);
  });

  it("puts Available gaps before, between and after Bookings", () => {
    const items = daySchedule(
      [
        booking("2026-10-20T09:00:00+03:00", "2026-10-20T10:00:00+03:00", "Sync"),
        booking("2026-10-20T11:00:00+03:00", "2026-10-20T12:00:00+03:00", "Review"),
      ],
      "2026-10-20",
    );

    expect(shape(items)).toEqual([
      ["available", "2026-10-19T21:00:00.000Z", "2026-10-20T06:00:00.000Z", null],
      ["booking", "2026-10-20T06:00:00.000Z", "2026-10-20T07:00:00.000Z", "Sync"],
      ["available", "2026-10-20T07:00:00.000Z", "2026-10-20T08:00:00.000Z", null],
      ["booking", "2026-10-20T08:00:00.000Z", "2026-10-20T09:00:00.000Z", "Review"],
      ["available", "2026-10-20T09:00:00.000Z", "2026-10-20T21:00:00.000Z", null],
    ]);
  });

  it("adds no empty gap between touching Bookings", () => {
    const items = daySchedule(
      [
        booking("2026-10-20T09:00:00+03:00", "2026-10-20T10:00:00+03:00", "First"),
        booking("2026-10-20T10:00:00+03:00", "2026-10-20T11:00:00+03:00", "Second"),
      ],
      "2026-10-20",
    );

    expect(items.map((item) => item.kind)).toEqual(["available", "booking", "booking", "available"]);
  });

  it("clips Bookings crossing midnight to the Day and flags them", () => {
    const items = daySchedule(
      [
        booking("2026-10-19T23:00:00+03:00", "2026-10-20T01:00:00+03:00", "From last night"),
        booking("2026-10-20T23:00:00+03:00", "2026-10-21T02:00:00+03:00", "Into tomorrow"),
      ],
      "2026-10-20",
    );

    expect(shape(items)).toEqual([
      ["booking", "2026-10-19T21:00:00.000Z", "2026-10-19T22:00:00.000Z", "From last night"],
      ["available", "2026-10-19T22:00:00.000Z", "2026-10-20T20:00:00.000Z", null],
      ["booking", "2026-10-20T20:00:00.000Z", "2026-10-20T21:00:00.000Z", "Into tomorrow"],
    ]);
    expect([items[0].startsBeforeDay, items[0].endsAfterDay]).toEqual([true, false]);
    expect([items[2].startsBeforeDay, items[2].endsAfterDay]).toEqual([false, true]);
  });
});

describe("recognising a Doha calendar date", () => {
  it("accepts a real YYYY-MM-DD date", () => {
    expect(isDohaDate("2026-10-20")).toBe(true);
    expect(isDohaDate("2028-02-29")).toBe(true);
  });

  it.each([null, "", "2026-02-30", "2026-1-5", "20-10-2026", "garbage"])("rejects %s", (value) => {
    expect(isDohaDate(value)).toBe(false);
  });
});

describe("formatting a duration", () => {
  it.each([
    [1, "1 minute"],
    [45, "45 minutes"],
    [60, "1 hour"],
    [90, "1 hour 30 minutes"],
    [120, "2 hours"],
    [241, "4 hours 1 minute"],
  ])("%i minutes reads %s", (minutes, text) => {
    expect(formatDuration(minutes)).toBe(text);
  });
});

describe("the next quarter hour, for a new Booking's default start", () => {
  it("rounds up to the next quarter of an hour", () => {
    expect(nextQuarterHour(new Date("2026-10-20T06:07:30Z")).toISOString()).toBe("2026-10-20T06:15:00.000Z");
  });

  it("moves on even when already exactly on a quarter", () => {
    expect(nextQuarterHour(new Date("2026-10-20T06:15:00Z")).toISOString()).toBe("2026-10-20T06:30:00.000Z");
  });

  it("can roll into the next Doha day", () => {
    const start = nextQuarterHour(new Date("2026-10-20T20:55:00Z")); // 23:55 in Doha
    expect([todayInDoha(start), formatDohaTime(start)]).toEqual(["2026-10-21", "00:00"]);
  });
});
