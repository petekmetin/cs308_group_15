import os

os.environ.setdefault("DJANGO_SECRET_KEY", "test-secret-key-for-sneaker-demo")

from .settings import *  # noqa: F401,F403


DEBUG = True
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
MEDIA_ROOT = BASE_DIR / "test-media"  # noqa: F405
