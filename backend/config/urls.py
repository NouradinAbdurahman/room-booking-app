from django.urls import include, path, re_path

from config.views import api_not_found

# Used when DEBUG is off; with DEBUG on, Django shows its technical page instead.
handler500 = "config.views.server_error"

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    path("api/rooms/", include("rooms.urls")),
    path("api/bookings/", include("bookings.urls")),
    # Anything else under /api/ answers in the error envelope, not Django's HTML 404.
    re_path(r"^api/", api_not_found),
]
