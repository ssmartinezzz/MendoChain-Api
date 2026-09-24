import json
import os
import subprocess
import sys

from django.conf import settings as current_settings
from django.test import SimpleTestCase

LOAD_SETTINGS = (
    "import json; from django.conf import settings; "
    "print(json.dumps({"
    "'DEBUG': settings.DEBUG, "
    "'ALLOWED_HOSTS': settings.ALLOWED_HOSTS, "
    "'DATABASE': settings.DATABASES['default'], "
    "'MIDDLEWARE': list(settings.MIDDLEWARE), "
    "'STORAGES': settings.STORAGES"
    "}, default=str))"
)

CONFIG_ENV_VARS = (
    'DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS', 'DATABASE_URL',
    'DB_NAME', 'DB_USER', 'DB_PASSWORD', 'DB_HOST', 'DB_PORT',
)


class SettingsFromEnvironmentTests(SimpleTestCase):
    """Settings are evaluated at import time, so each case loads them in a fresh process."""

    def load_settings(self, **env):
        base_env = {
            key: value for key, value in os.environ.items()
            if key not in CONFIG_ENV_VARS
        }
        base_env['DJANGO_SETTINGS_MODULE'] = 'api.settings'
        base_env.update(env)
        return subprocess.run(
            [sys.executable, '-c', LOAD_SETTINGS],
            cwd=current_settings.BASE_DIR,
            env=base_env,
            capture_output=True,
            text=True,
        )

    def test_debug_is_off_by_default(self):
        result = self.load_settings(SECRET_KEY='test')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['DEBUG'])

    def test_debug_can_be_enabled_from_environment(self):
        result = self.load_settings(SECRET_KEY='test', DEBUG='true')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['DEBUG'])

    def test_missing_secret_key_fails_to_start(self):
        result = self.load_settings()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('SECRET_KEY', result.stderr)

    def test_allowed_hosts_come_from_environment(self):
        result = self.load_settings(SECRET_KEY='test', ALLOWED_HOSTS='api.example.com, localhost')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['ALLOWED_HOSTS'], ['api.example.com', 'localhost'])

    def test_allowed_hosts_never_default_to_wildcard(self):
        result = self.load_settings(SECRET_KEY='test')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('*', json.loads(result.stdout)['ALLOWED_HOSTS'])

    def test_database_url_takes_precedence(self):
        result = self.load_settings(
            SECRET_KEY='test',
            DATABASE_URL='postgres://mendo:secret@db.example.com:5433/mendochain',
            DB_NAME='ignored',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        database = json.loads(result.stdout)['DATABASE']
        self.assertEqual(database['ENGINE'], 'django.db.backends.postgresql')
        self.assertEqual(database['NAME'], 'mendochain')
        self.assertEqual(database['HOST'], 'db.example.com')
        self.assertEqual(int(database['PORT']), 5433)

    def test_database_falls_back_to_individual_variables(self):
        result = self.load_settings(
            SECRET_KEY='test', DB_NAME='mendochain', DB_USER='mendo',
            DB_PASSWORD='secret', DB_HOST='db', DB_PORT='5432',
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        database = json.loads(result.stdout)['DATABASE']
        self.assertEqual(database['NAME'], 'mendochain')
        self.assertEqual(database['USER'], 'mendo')
        self.assertEqual(database['HOST'], 'db')

    def test_database_host_defaults_to_localhost(self):
        result = self.load_settings(SECRET_KEY='test', DB_NAME='mendochain')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['DATABASE']['HOST'], 'localhost')

    def test_whitenoise_serves_static_files_right_after_security_middleware(self):
        result = self.load_settings(SECRET_KEY='test')
        self.assertEqual(result.returncode, 0, result.stderr)
        middleware = json.loads(result.stdout)['MIDDLEWARE']
        security_index = middleware.index('django.middleware.security.SecurityMiddleware')
        self.assertEqual(middleware[security_index + 1], 'whitenoise.middleware.WhiteNoiseMiddleware')

    def test_static_files_use_compressed_manifest_storage(self):
        result = self.load_settings(SECRET_KEY='test')
        self.assertEqual(result.returncode, 0, result.stderr)
        storages = json.loads(result.stdout)['STORAGES']
        self.assertEqual(
            storages['staticfiles']['BACKEND'],
            'whitenoise.storage.CompressedManifestStaticFilesStorage',
        )


class CorsTests(SimpleTestCase):

    def test_allowed_origin_receives_cors_header(self):
        response = self.client.get('/api/hello_world', HTTP_ORIGIN='http://localhost:3000')
        self.assertEqual(response['Access-Control-Allow-Origin'], 'http://localhost:3000')

    def test_unknown_origin_does_not_receive_cors_header(self):
        response = self.client.get('/api/hello_world', HTTP_ORIGIN='https://evil.example.com')
        self.assertNotIn('Access-Control-Allow-Origin', response)
