"""
Test settings - uses SQLite for fast local testing.
"""

import os

# Required environment variables read by api.settings
os.environ["DJANGO_SECRET_KEY"] = "test-secret-key"
os.environ["DB_NAME"] = "app"
os.environ["DB_USERNAME"] = "postgres"
os.environ["DB_PASSWORD"] = "postgres"
os.environ["DB_HOST"] = "db"
os.environ["AI_ENABLED"] = "true"

# Import all settings from main settings
from api.settings import *  # noqa

# Override database to use SQLite for tests
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}


# Disable migrations for faster tests
class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


MIGRATION_MODULES = DisableMigrations()

# Use in-memory cache for tests (no Redis dependency)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# Faster password hasher for tests
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

# Disable logging during tests
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "root": {
        "handlers": ["null"],
        "level": "DEBUG",
    },
}
