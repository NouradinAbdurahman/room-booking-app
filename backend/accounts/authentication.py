from rest_framework import authentication, exceptions


class CsrfFailed(exceptions.PermissionDenied):
    default_detail = "CSRF check failed. Reload the page and try again."
    default_code = "csrf_failed"


def enforce_csrf(request):
    """Run Django's CSRF check on a DRF request, raising CsrfFailed on failure.

    Used for every authenticated session request and, explicitly, for login:
    DRF skips CSRF for anonymous requests and every DRF view is csrf_exempt.
    """
    try:
        authentication.SessionAuthentication().enforce_csrf(request)
    except exceptions.PermissionDenied as exc:
        raise CsrfFailed() from exc


class ApiSessionAuthentication(authentication.SessionAuthentication):
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
        enforce_csrf(request)
