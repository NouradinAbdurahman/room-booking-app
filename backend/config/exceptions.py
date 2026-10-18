"""One error envelope for every API error (ADR 0006).

    {"error": {"code": "...", "message": "...", "fields": {...}}}
"""

from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

VALIDATION_MESSAGE = "Some fields are invalid."


def exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, (exceptions.ValidationError, exceptions.ParseError)):
        code = "validation_error"
        message, fields = _validation_message_and_fields(exc.detail)
    else:
        code = exc.default_code if isinstance(exc, exceptions.APIException) else "error"
        message = _first_message(exc.detail) if hasattr(exc, "detail") else str(exc)
        fields = {}

    response.data = {"error": {"code": code, "message": message, "fields": fields}}
    return response


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
