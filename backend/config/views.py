from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny

from config.exceptions import error_body


@api_view(["GET", "POST", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def api_not_found(request):
    raise NotFound()


# Django's own error views, for failures that never reach DRF (e.g. a Host
# not in ALLOWED_HOSTS) or that DRF does not handle (an unexpected exception).
# They still answer in the error envelope (ADR 0006) and never show internal
# detail; Django logs the full traceback of a 500 on the server.


def bad_request(request, exception=None):
    return JsonResponse(error_body("bad_request", "The request could not be understood."), status=400)


def permission_denied(request, exception=None):
    return JsonResponse(error_body("permission_denied", "You do not have permission to do this."), status=403)


def server_error(request):
    return JsonResponse(
        error_body("server_error", "Something went wrong on our side. Please try again."), status=500
    )
