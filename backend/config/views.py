from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import NotFound
from rest_framework.permissions import AllowAny


@api_view(["GET", "POST", "PUT", "PATCH", "DELETE"])
@permission_classes([AllowAny])
def api_not_found(request):
    raise NotFound()


def server_error(request):
    """Unexpected errors still answer in the error envelope (ADR 0006), with no
    internal detail; Django logs the full traceback on the server."""
    return JsonResponse(
        {
            "error": {
                "code": "server_error",
                "message": "Something went wrong on our side. Please try again.",
                "fields": {},
            }
        },
        status=500,
    )
