# Ticket 12: security and API-consistency checklist

Checked on 2026-10-19 against commit range `58a37ad..HEAD`. Each item says how it was checked, so it can be re-run.

| Check | Result | How it was checked |
| --- | --- | --- |
| No CORS | None in the backend | `grep -rniE cors backend --include='*.py' --include='*.txt'` (no matches outside tests); `requirements.txt` has no `django-cors-headers` |
| PostgreSQL not published | Only `5173` and `8000` published | `docker compose config` → `db` has no `ports` |
| No secrets committed | `.env` untracked; `.env.example` holds only values marked "LOCAL DEMO VALUE" | `git ls-files`; `git grep` for hard-coded secrets/passwords outside tests |
| Production-safe settings when `DEBUG` is off | Only `security.W021` (HSTS preload) remains, deliberately off per ADR 0004 | `manage.py check --deploy` with `DJANGO_DEBUG=False` |
| No SQL injection surface | No raw SQL, `cursor()`, `RawSQL` or `.extra()` in application code (only in tests that provoke real database errors); the `btree_gist` extension uses Django's own migration operation | `grep -rnE "\.raw\(|cursor\(|RawSQL|\.extra\(|execute\(" backend --include='*.py'`, excluding tests |
| No XSS surface in the UI | No `dangerouslySetInnerHTML`, `innerHTML` or `eval`; titles and usernames render as plain JSX text, which React escapes | `grep -rnE "dangerouslySetInnerHTML|innerHTML|eval\(" frontend/src` |
| Passwords never logged | No `print`/logging of request data in application code; login marks POST parameters sensitive and hides its frame locals from error reports (the password arrives as JSON) | `grep` for `print(`, `logger.`, `logging.` in application code; `accounts/views.py` decorators |
| One error envelope everywhere | Every error answers `{"error": {"code", "message", "fields"}}`, including Django-level 400/403/500 when `DEBUG` is off | `tests/test_error_envelope_sweep.py` (28 cases) |
| No missing migrations | Models and migrations agree | `manage.py makemigrations --check --dry-run` → "No changes detected" |
| Cross-user access | None beyond the intended shared schedule; Booker-only cancel; the User always comes from the session; clients cannot set the Booker, status or `cancelled_at` | Focused security review of the whole app (no blocking findings) + Seam 1 tests |

## Error codes beyond the spec's table (additive, same envelope)

| Status | Code | When |
| --- | --- | --- |
| `400` | `bad_request` | Django refuses a request before the API runs, e.g. a `Host` not in `ALLOWED_HOSTS` |
| `403` | `permission_denied` | Django-level permission failure outside the API's own checks |
| `415` | `unsupported_media_type` | A body that is not JSON (e.g. form-encoded) |
| `500` | `server_error` | An unexpected server error; no internal detail is sent, and Django logs the traceback |

## Known limits (not changed in ticket 12)

- With `DEBUG=True` (local development), Django shows its own technical pages for 400/403/500 instead of the envelope, as Django intends. Production runs with `DEBUG` off.
- Unknown extra query parameters are ignored, not refused. A stricter rule needs the user's approval.
- Creating Bookings has no per-User rate limit; only login is throttled (spec §3). Raised by the security review; needs the user's approval because it is a new rule.
- The login throttle trusts one proxy hop (`NUM_PROXIES=1`); direct calls to port `8000` could forge `X-Forwarded-For` (ADR 0004, accepted trade-off).
