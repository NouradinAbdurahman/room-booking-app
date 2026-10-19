# 04: Login screen, navy shell and CSRF-aware API client

**What to build:** A User opens the app, logs in on the Login screen, and lands in the app shell with the dark navy sidebar. They stay logged in after reloading, can log out, and are sent back to Login when their session ends. All HTTP goes through one API client that always sends the **current** CSRF token (spec §6; ADR 0004; visual 8 panels 1 and 2, and `docs/design/README.md`).

**Blocked by:** 02

**Status:** done

- [ ] **API client:**
  - Reads the `csrftoken` cookie **at send time** on every unsafe request and sends it as `X-CSRFToken`. It never caches the token.
  - Sends no CSRF header on `GET`.
  - Calls the CSRF bootstrap when no cookie is present (on app start and after logout).
  - Follows `next` until it is null.
  - Turns the error envelope into a message plus field errors.
  - Reports `401` so the app can redirect to Login.
- [ ] **Design tokens** are defined once in CSS (navy sidebar, light grey and white content, bright-blue primary, pastel booking colours, green and red banners), taken from visual 8.
- [ ] **Login screen** matches visual 8 panel 1: app icon and title, username, password with a show/hide toggle, a Login button, and the API's error message ("Invalid username or password.").
- [ ] **Shell** matches visual 8: a navy sidebar with Rooms, My Bookings and Logout. Routes are protected, and any `401` redirects to Login. On reload, `GET /api/auth/me/` restores the session.
- [ ] Vitest tests for the API client, using a fake `fetch`, cover:
  - following `next`;
  - sending the CSRF header on unsafe methods only;
  - **the stale-token test:** the cookie value changes between two unsafe requests, and the second request carries the new value;
  - bootstrapping when no cookie is present;
  - error-envelope parsing;
  - `401` reporting.
- [ ] **Manual check in a real browser through the Vite proxy:** bootstrap → login → logout → login works with no CSRF errors. The result is noted for the README.
