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
  - `Secure` cookies, HSTS and the HTTPS redirect when `DEBUG` is off (see below).
  - `CSRF_TRUSTED_ORIGINS=['http://localhost:5173']`.
  - `ALLOWED_HOSTS` comes from the environment.
- Production-safe settings come from environment variables, with `DEBUG` off by default. No secrets are in the repo, apart from clearly marked demo values in `.env.example`.
- **`DEBUG=False` requires the app to be served over HTTPS.** Local development runs with `DEBUG=True`. Deployment is out of scope, so this describes what a deployment would need, not one that exists.
  - With `DEBUG` off: the HTTP→HTTPS redirect is on, the session and CSRF cookies are `Secure`, and HSTS is one year with `includeSubDomains`. Over plain HTTP, including direct API checks on port `8000`, every request is redirected.
  - `includeSubDomains` assumes the deployment controls every subdomain of its host.
  - HSTS preload stays off (Django deploy check W021), because it is hard to reverse and needs a real domain.
  - `SECURE_PROXY_SSL_HEADER` stays unset. It is only safe once a known HTTPS proxy is confirmed to strip client-supplied `X-Forwarded-Proto`. Until it is set, Django must see HTTPS directly; behind a TLS-terminating proxy, the redirect would loop.
- Docker Compose publishes only the frontend (`5173`) and backend (`8000`, for direct API checks) ports. PostgreSQL is reachable only inside the Compose network and is never published to the host.
- To verify during implementation:
  - An end-to-end test of the CSRF bootstrap → login → authenticated `POST` flow.
  - A test that a `POST` without the token is refused.
  - A manual check that Django's CSRF origin check passes through the Vite proxy. This depends on how the proxy forwards the `Host` and `Origin` headers.
