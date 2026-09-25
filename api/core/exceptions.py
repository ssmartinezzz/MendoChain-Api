from django.http import Http404, JsonResponse
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from .errors import ConflictError, DomainError, NotFoundError, UnavailableError

DOMAIN_ERROR_STATUS = (
    (NotFoundError, status.HTTP_404_NOT_FOUND),
    (ConflictError, status.HTTP_409_CONFLICT),
    (UnavailableError, status.HTTP_502_BAD_GATEWAY),
)


def error_body(code, message, details=None):
    return {'error': {'code': code, 'message': message, 'details': details}}


def exception_handler(exc, context):
    """Render every handled error as {"error": {"code", "message", "details"}}."""
    if isinstance(exc, DomainError):
        return Response(error_body(exc.code, exc.message), status=_domain_error_status(exc))

    if isinstance(exc, Http404):
        exc = exceptions.NotFound()

    response = drf_exception_handler(exc, context)
    if response is None:
        return None

    if isinstance(exc, exceptions.ValidationError):
        response.data = error_body('invalid', 'Invalid input.', response.data)
    else:
        response.data = error_body(exc.get_codes(), str(exc.detail))
    return response


def _domain_error_status(exc):
    for error_type, status_code in DOMAIN_ERROR_STATUS:
        if isinstance(exc, error_type):
            return status_code
    return status.HTTP_400_BAD_REQUEST


def not_found_view(request, exception=None):
    return JsonResponse(error_body('not_found', 'Not found.'), status=status.HTTP_404_NOT_FOUND)


def server_error_view(request):
    return JsonResponse(
        error_body('server_error', 'Internal server error.'), status=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )
