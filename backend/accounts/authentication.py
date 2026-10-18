from rest_framework import authentication, exceptions


class CsrfFailed(exceptions.PermissionDenied):
    default_detail = "CSRF check failed. Reload the page and try again."
    default_code = "csrf_failed"


class SessionAuthentication(authentication.SessionAuthentication):
    """DRF session authentication with two fixes (ADR 0004, spec §3).

    - Logged-out requests get 401, not 403: DRF only answers 401 when the
      first authentication class names a WWW-Authenticate challenge. It is
      deliberately not "Basic", which would make browsers show a login prompt.
    - CSRF failures raise their own exception so the error handler can map
      them to `csrf_failed` without matching on message text.
    """

    def authenticate_header(self, request):
        return "Session"

    def enforce_csrf(self, request):
        try:
            super().enforce_csrf(request)
        except exceptions.PermissionDenied as exc:
            raise CsrfFailed() from exc
