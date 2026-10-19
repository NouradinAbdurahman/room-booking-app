# 12: API consistency and security sweep

**What to build:** A reviewer checking the CTO's engineering standards finds every endpoint consistent and every security point met. Any gaps found in earlier tickets are closed here (brief "Engineering standards"; spec acceptance criteria 13–20; ADRs 0004, 0006).

**Blocked by:** 11

**Status:** done

- [ ] Seam 1 › Error envelope: for every endpoint, every error it can produce is checked for the envelope, status and code:
  - `400 validation_error` and `invalid_credentials`;
  - `401 not_authenticated` with its header;
  - `403 csrf_failed` and `not_booker`;
  - `404 not_found`;
  - `405 method_not_allowed`;
  - `409 booking_conflict`;
  - `429 throttled`;
  - a malformed JSON body.
- [ ] Review checks, recorded as a short checklist for the README:
  - no CORS package or settings;
  - `db` has no published port;
  - no secrets committed beyond marked demo values;
  - production-safe settings when `DEBUG` is off;
  - `dangerouslySetInnerHTML` is never used;
  - no raw SQL apart from the extension migration;
  - passwords are not logged.
- [ ] A basic mobile pass: below a narrow width the sidebar collapses into a top bar, and every screen is usable on a phone-sized viewport (visual 8 panel 7, kept basic).
- [ ] Any gap found is fixed in its own small commit.
