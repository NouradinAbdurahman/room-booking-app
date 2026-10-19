import { addDays, dohaDayBounds, formatDohaDate } from "../utils/dohaTime.js";
import { CalendarIcon, ChevronLeftIcon, ChevronRightIcon } from "./Icons.jsx";

/** Previous Day / date picker / next Day, all on Doha calendar dates ("YYYY-MM-DD"). */
export default function DateStepper({ date, onChange }) {
  return (
    <div className="date-stepper">
      <button type="button" aria-label="Previous day" onClick={() => onChange(addDays(date, -1))}>
        <ChevronLeftIcon />
      </button>
      <label className="date-stepper__picker">
        <CalendarIcon width={18} height={18} />
        <span>{formatDohaDate(dohaDayBounds(date).start)}</span>
        <input
          type="date"
          aria-label="Choose a date"
          value={date}
          onChange={(e) => e.target.value && onChange(e.target.value)}
          onClick={(e) => e.currentTarget.showPicker?.()}
        />
      </label>
      <button type="button" aria-label="Next day" onClick={() => onChange(addDays(date, 1))}>
        <ChevronRightIcon />
      </button>
    </div>
  );
}
