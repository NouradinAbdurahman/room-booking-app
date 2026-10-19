import { useState } from "react";
import { api } from "../api/index.js";

/**
 * Cancel one of the User's own Bookings, after an in-app confirmation
 * (never the browser's confirm()). The server decides; its answer is passed on.
 */
export default function CancelBookingButton({ booking, onCancelled, onFailed }) {
  const [step, setStep] = useState("idle"); // idle -> confirming -> sending

  async function confirm() {
    setStep("sending");
    try {
      await api.delete(`/api/bookings/${booking.id}/`);
      setStep("idle");
      onCancelled(booking);
    } catch (err) {
      setStep("idle");
      onFailed(err);
    }
  }

  if (step === "idle") {
    return (
      <button type="button" className="button button--danger button--small" onClick={() => setStep("confirming")}>
        Cancel
      </button>
    );
  }

  return (
    <span className="cancel-confirm" role="group" aria-label={`Cancel ${booking.title}?`}>
      <span>Cancel this booking?</span>
      <button type="button" className="button button--danger-solid button--small" onClick={confirm} disabled={step === "sending"}>
        {step === "sending" ? "Cancelling…" : "Yes, cancel"}
      </button>
      <button type="button" className="button button--secondary button--small" onClick={() => setStep("idle")} disabled={step === "sending"}>
        Keep
      </button>
    </span>
  );
}
