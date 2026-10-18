import { describe, expect, it } from "vitest";
import {
  addDays,
  clipToDay,
  dohaDayBounds,
  durationMinutes,
  formatDohaDate,
  formatDohaTime,
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
    expect(durationMinutes(toDohaIso("2026-10-18", "10:00"), toDohaIso("2026-10-18", "11:30"))).toBe(90);
  });

  it("counts across midnight", () => {
    expect(durationMinutes(toDohaIso("2026-10-18", "22:00"), toDohaIso("2026-10-19", "01:00"))).toBe(180);
  });
});

describe("clipping a Booking to the Day being shown", () => {
  const lateNight = { start: "2026-10-18T22:00:00+03:00", end: "2026-10-19T01:00:00+03:00" };

  it("cuts a Booking that crosses midnight at the end of its first Day", () => {
    const clipped = clipToDay(lateNight, "2026-10-18");

    expect(formatDohaTime(clipped.start)).toBe("22:00");
    expect(clipped.end.toISOString()).toBe("2026-10-18T21:00:00.000Z"); // Doha midnight
    expect(clipped.startsBeforeDay).toBe(false);
    expect(clipped.endsAfterDay).toBe(true);
  });

  it("starts the same Booking at midnight on its second Day", () => {
    const clipped = clipToDay(lateNight, "2026-10-19");

    expect(clipped.start.toISOString()).toBe("2026-10-18T21:00:00.000Z");
    expect(formatDohaTime(clipped.end)).toBe("01:00");
    expect(clipped.startsBeforeDay).toBe(true);
    expect(clipped.endsAfterDay).toBe(false);
  });

  it("leaves a Booking inside the Day untouched", () => {
    const clipped = clipToDay(
      { start: "2026-10-18T09:00:00+03:00", end: "2026-10-18T10:00:00+03:00" },
      "2026-10-18",
    );

    expect([formatDohaTime(clipped.start), formatDohaTime(clipped.end)]).toEqual(["09:00", "10:00"]);
    expect([clipped.startsBeforeDay, clipped.endsAfterDay]).toEqual([false, false]);
  });
});
