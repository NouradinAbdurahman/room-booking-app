from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import exceptions, serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from .authentication import SessionAuthentication


class InvalidCredentials(exceptions.APIException):
    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "Invalid username or password."
    default_code = "invalid_credentials"


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(trim_whitespace=False)


def user_payload(user):
    return {"id": user.id, "username": user.username}


class CsrfView(APIView):
    """Sets the csrftoken cookie the SPA must send back on unsafe requests."""

    permission_classes = [AllowAny]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


@method_decorator(sensitive_post_parameters("password"), name="dispatch")
class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    def post(self, request):
        # DRF skips CSRF for anonymous requests (and every DRF view is
        # csrf_exempt), so login runs the same check explicitly, before it
        # reads any credentials (ADR 0004).
        SessionAuthentication().enforce_csrf(request)

        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(request._request, **serializer.validated_data)
        if user is None:
            raise InvalidCredentials()

        # Rotates the session id and the CSRF token.
        login(request._request, user)
        return Response({"user": user_payload(user)})


class MeView(APIView):
    def get(self, request):
        return Response(user_payload(request.user))


class LogoutView(APIView):
    def post(self, request):
        logout(request._request)
        return Response(status=status.HTTP_204_NO_CONTENT)
