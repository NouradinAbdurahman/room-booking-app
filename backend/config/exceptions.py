"""One error envelope for every API error (ADR 0006).

    {"error": {"code": "...", "message": "...", "fields": {...}}}
"""

from django.core.exceptions import PermissionDenied as DjangoPermissionDenied
from django.http import Http404
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

VALIDATION_MESSAGE = "Some fields are invalid."
PARSE_ERROR_MESSAGE = "The request body is not valid JSON."


def exception_handler(exc, context):
    # DRF converts Django's own 404/403 internally but hands us the original
    # exception; convert first so their code and message come out right.
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    elif isinstance(exc, DjangoPermissionDenied):
        exc = exceptions.PermissionDenied()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ParseError):
        code, message, fields = "validation_error", PARSE_ERROR_MESSAGE, {}
    elif isinstance(exc, exceptions.ValidationError):
        code = "validation_error"
        message, fields = _validation_message_and_fields(exc.detail)
    else:
        code, message, fields = _code(exc), _first_message(exc.detail), {}

    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response


def _code(exc):
    # A code passed when raising (e.g. PermissionDenied(code=...)) wins over the class default.
    codes = exc.get_codes()
    return codes if isinstance(codes, str) else exc.default_code


def _validation_message_and_fields(detail):
    if not isinstance(detail, dict):
        return _first_message(detail), {}
    fields = {name: [str(m) for m in _as_list(messages)] for name, messages in detail.items()}
    non_field = fields.pop("non_field_errors", None)
    return (non_field[0] if non_field else VALIDATION_MESSAGE), fields


def _first_message(detail):
    if isinstance(detail, dict):
        detail = next(iter(detail.values()), "")
    if isinstance(detail, list):
        detail = detail[0] if detail else ""
    return str(detail)


def _as_list(messages):
    return messages if isinstance(messages, list) else [messages]
