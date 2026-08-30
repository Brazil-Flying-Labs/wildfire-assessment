"""Tests for the environment-based settings configuration (no AWS)."""

import os
import subprocess
import sys
from pathlib import Path

from django.test import SimpleTestCase

API_DIR = Path(__file__).resolve().parents[2]


class SettingsConfigTests(SimpleTestCase):
    """Validate that settings load from environment variables only."""

    def _import_settings_in_subprocess(self, env):
        """Import api.settings in a clean subprocess; returns (code, stderr)."""
        return subprocess.run(
            [sys.executable, "-c", "import api.settings"],
            capture_output=True,
            text=True,
            env=env,
            cwd=str(API_DIR),
        )

    def test_settings_fail_without_secret_key(self):
        """Importing settings without DJANGO_SECRET_KEY raises a clear error."""
        env = dict(os.environ)
        env.pop("DJANGO_SECRET_KEY", None)
        result = self._import_settings_in_subprocess(env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", result.stderr)

    def test_settings_fail_without_database_vars(self):
        """Importing settings without the DB_* variables raises a clear error."""
        env = dict(os.environ)
        env.pop("DB_NAME", None)
        result = self._import_settings_in_subprocess(env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("DB_NAME", result.stderr)
