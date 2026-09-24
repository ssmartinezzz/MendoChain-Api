import logging
import re
import time
import uuid

logger = logging.getLogger('api.request')

REQUEST_ID_HEADER = 'X-Request-ID'
SAFE_REQUEST_ID = re.compile(r'^[A-Za-z0-9._-]{1,128}$')


class RequestIdMiddleware:
    """Tags each request with an id (reused from a safe incoming header) and logs one line per request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = self._request_id(request)
        started = time.monotonic()

        response = self.get_response(request)

        response[REQUEST_ID_HEADER] = request.request_id
        logger.info(
            '%s %s %s duration_ms=%d request_id=%s',
            request.method,
            request.path,
            response.status_code,
            (time.monotonic() - started) * 1000,
            request.request_id,
        )
        return response

    @staticmethod
    def _request_id(request):
        incoming = request.headers.get(REQUEST_ID_HEADER, '')
        if SAFE_REQUEST_ID.match(incoming):
            return incoming
        return uuid.uuid4().hex
