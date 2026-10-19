# 02: Error envelope and session auth API with explicit CSRF

**What to build:** A demo User can log in and out through the API using a session cookie. CSRF is enforced on **every** unsafe request, login included, and the token rotates on login. Logged-out requests get `401`, never `403`. Every error, from any source, uses one envelope (spec §3, §4; ADRs 0004, 0006; visuals 6 and 7).

**Blocked by:** 01

**Status:** done

- [ ] One exception handler renders every non-2xx response as `{"error": {"code", "message", "fields"}}`, including DRF's built-in errors (auth, permission, not found, method not allowed, throttle, parse, validation).
- [ ] The project's session authentication class (a subclass of DRF's `SessionAuthentication`) is the only authentication class, and "authenticated" is the default permission. It:
  - returns `WWW-Authenticate: Session` (not `Basic`), so logged-out requests get `401 not_authenticated`;
  - raises a dedicated CSRF-failed exception, mapped to `403 csrf_failed` without matching on message text.
- [ ] `GET /api/auth/csrf/` (anonymous) sets a `csrftoken` cookie that JavaScript can read.
- [ ] `POST /api/auth/login/` (anonymous) runs the CSRF check itself **before** reading credentials, because DRF skips CSRF for anonymous requests.
  - Success: calls Django's `login`, which rotates the session and the CSRF token, and returns `200 {"user": {"id", "username"}}`.
  - Wrong credentials: `400 invalid_credentials`, with a message that doesn't reveal whether the username exists.
  - Request parameters are marked sensitive, so the password is never logged.
  - A DRF scoped throttle allows 5 attempts per minute; the next gets `429 throttled`.
- [ ] `POST /api/auth/logout/` returns `204`. `GET /api/auth/me/` returns `{"id", "username"}`.
- [ ] Cookie flags: the session cookie is `HttpOnly`, both cookies are `SameSite=Lax`, both are `Secure` when `DEBUG` is off. `CSRF_TRUSTED_ORIGINS` includes `http://localhost:5173`.
- [ ] An idempotent demo-seed command, run on backend start, creates `user1`, `user2` and `user3` with the password from `DEMO_USER_PASSWORD`. Passwords are stored hashed.
- [ ] Tests T-AUTH-1 to T-AUTH-8 from the spec pass on PostgreSQL, using a client with CSRF checks enforced. Together they cover:
  - `401` with the header;
  - bootstrap → login → a new token that differs from the bootstrap one;
  - a stale pre-login token is refused;
  - login without a token, or with a wrong one, is refused even with correct credentials;
  - an authenticated unsafe request without a token is refused;
  - invalid credentials;
  - the throttle;
  - logout.
  
  Because no booking endpoint exists yet, T-AUTH-2, T-AUTH-3 and T-AUTH-5 use logout as the authenticated unsafe request for now. Ticket 08 extends them to `POST` bookings.
