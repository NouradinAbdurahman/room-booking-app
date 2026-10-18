# Django session authentication over a single origin, with CORS disabled

The React app authenticates with Django's built-in session cookie (`HttpOnly`), not with tokens or JWTs held in JavaScript. A script injected into the page cannot read an `HttpOnly` cookie, and Django's mature CSRF protection covers the one weakness of cookies.

The browser only ever talks to one origin, `http://localhost:5173`. The Vite dev server proxies `/api` to the Django container, so the browser never makes a cross-origin request. CORS is therefore never enabled: no `django-cors-headers` and no `CORS_ALLOWED_ORIGINS`. That is the strictest possible answer to "no open CORS".

## CSRF flow

1. The SPA calls `GET /api/auth/csrf/` on load, which sets the `csrftoken` cookie.
2. Every unsafe request, including `POST /api/auth/login/`, sends the token in the `X-CSRFToken` header.
3. Login rotates the session and the CSRF token. The SPA re-reads the token afterwards.

## Considered options

- **JWT or DRF tokens in `localStorage`.** Rejected. Any XSS bug can steal the token, and logout or revocation needs extra machinery.
- **Separate origins with `django-cors-headers`.** Rejected. It needs an origin allow-list, credentialed CORS and cross-site cookie settings: more configuration and more ways to get it wrong, for no benefit in this app.

## Consequences

- Every endpoint except the CSRF bootstrap and login requires a logged-in user. Anonymous requests get `401`. The user is always taken from the session on the server, never from a request parameter.
- The login endpoint gets DRF's scoped throttle to slow down password guessing.
- Cookie and host settings:
  - `SESSION_COOKIE_HTTPONLY=True`.
  - `SameSite=Lax` on both the session and CSRF cookies.
  - `Secure` cookies and HSTS when `DEBUG` is off.
  - `CSRF_TRUSTED_ORIGINS=['http://localhost:5173']`.
  - `ALLOWED_HOSTS` comes from the environment.
- Production-safe settings come from environment variables, with `DEBUG` off by default. No secrets are in the repo, apart from clearly marked demo values in `.env.example`.
- Docker Compose publishes only the frontend (`5173`) and backend (`8000`, for direct API checks) ports. PostgreSQL is reachable only inside the Compose network and is never published to the host.
- To verify during implementation:
  - An end-to-end test of the CSRF bootstrap → login → authenticated `POST` flow.
  - A test that a `POST` without the token is refused.
  - A manual check that Django's CSRF origin check passes through the Vite proxy. This depends on how the proxy forwards the `Host` and `Origin` headers.
