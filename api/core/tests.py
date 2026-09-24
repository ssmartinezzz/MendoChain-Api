from django.contrib.auth.models import User
from django.test import SimpleTestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, APITestCase
from rest_framework.views import APIView

from api.core.errors import NotFoundError, UnavailableError


class RaisesNotFound(APIView):
    permission_classes = []

    def get(self, request):
        raise NotFoundError('wine_not_found', 'Wine 7 does not exist.')


class RaisesUnavailable(APIView):
    permission_classes = []

    def get(self, request):
        raise UnavailableError('ledger_unavailable', 'The ledger could not be reached.')


class ErrorEnvelopeForDomainErrorsTests(SimpleTestCase):
    factory = APIRequestFactory()

    def test_not_found_domain_error_maps_to_404(self):
        response = RaisesNotFound.as_view()(self.factory.get('/'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data, {'error': {
            'code': 'wine_not_found', 'message': 'Wine 7 does not exist.', 'details': None,
        }})

    def test_unavailable_domain_error_maps_to_502(self):
        response = RaisesUnavailable.as_view()(self.factory.get('/'))
        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertEqual(response.data['error']['code'], 'ledger_unavailable')


class ErrorEnvelopeForFrameworkErrorsTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='user@test.com', password='pass12345!')

    def test_missing_resource(self):
        response = self.client.get('/api/wine/9999')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error']['code'], 'not_found')
        self.assertIsNone(response.json()['error']['details'])

    def test_validation_error_lists_fields_in_details(self):
        self.client.force_authenticate(self.user)
        response = self.client.post('/api/wine', {'variety_name': 'Malbec'})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        error = response.json()['error']
        self.assertEqual(error['code'], 'invalid')
        self.assertIn('brand_name', error['details'])

    def test_unauthenticated_keeps_www_authenticate_header(self):
        response = self.client.delete('/api/wine/1')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()['error']['code'], 'not_authenticated')
        self.assertIn('WWW-Authenticate', response)

    def test_method_not_allowed(self):
        self.client.force_authenticate(self.user)
        response = self.client.put('/api/transaction/1', {})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)
        self.assertEqual(response.json()['error']['code'], 'method_not_allowed')

    def test_unknown_url_returns_json_envelope(self):
        response = self.client.get('/does-not-exist')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.json()['error']['code'], 'not_found')


class RequestIdMiddlewareTests(SimpleTestCase):
    url = '/api/hello_world'

    def test_generates_request_id_when_missing(self):
        response = self.client.get(self.url)
        self.assertRegex(response['X-Request-ID'], r'^[0-9a-f]{32}$')

    def test_propagates_safe_incoming_request_id(self):
        response = self.client.get(self.url, HTTP_X_REQUEST_ID='frontend-abc.123')
        self.assertEqual(response['X-Request-ID'], 'frontend-abc.123')

    def test_replaces_unsafe_incoming_request_id(self):
        for unsafe in ('evil value; injected', 'x' * 129, ''):
            with self.subTest(unsafe=unsafe):
                response = self.client.get(self.url, HTTP_X_REQUEST_ID=unsafe)
                self.assertRegex(response['X-Request-ID'], r'^[0-9a-f]{32}$')

    def test_logs_one_line_per_request(self):
        with self.assertLogs('api.request', level='INFO') as logs:
            response = self.client.get(self.url, HTTP_X_REQUEST_ID='trace-1')
        self.assertEqual(len(logs.output), 1)
        line = logs.output[0]
        self.assertIn('GET /api/hello_world 200', line)
        self.assertIn('request_id=trace-1', line)
        self.assertRegex(line, r'duration_ms=\d+')
        self.assertEqual(response.status_code, 200)

    def test_request_id_is_exposed_to_allowed_origins(self):
        response = self.client.get(self.url, HTTP_ORIGIN='http://localhost:3000')
        self.assertIn('x-request-id', response['Access-Control-Expose-Headers'].lower())
