from django.urls import include, path, re_path

from config.views import api_not_found

urlpatterns = [
    path("api/auth/", include("accounts.urls")),
    # Anything else under /api/ answers in the error envelope, not Django's HTML 404.
    re_path(r"^api/", api_not_found),
]
