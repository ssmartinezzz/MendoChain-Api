import json
import os
import subprocess
import sys

from django.conf import settings as current_settings
from django.test import SimpleTestCase

LOAD_SETTINGS = (
    "import json; from django.conf import settings; "
    "print(json.dumps({'DEBUG': settings.DEBUG, 'ALLOWED_HOSTS': settings.ALLOWED_HOSTS}))"
)


class SettingsFromEnvironmentTests(SimpleTestCase):
    """Settings are evaluated at import time, so each case loads them in a fresh process."""

    def load_settings(self, **env):
        base_env = {
            key: value for key, value in os.environ.items()
            if key not in ('DEBUG', 'SECRET_KEY', 'ALLOWED_HOSTS')
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
