"""
Django settings for the AccessPath backend.

Every value that changes between laptops, staging and production comes from
environment variables (see .env.example). Nothing secret is written here.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY", default="dev-only-not-secret")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    # Lane A, platform and identity
    "apps.accounts",
    "apps.classes",
    "apps.storage",
    # Lane B, ingestion
    "apps.uploads",
    # Lane C, AI processing
    "apps.pipeline",
    # Lane D, review
    "apps.review",
    # Lane E, export and accessibility
    "apps.exports",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Postgres in Docker and in production. Falls back to a local SQLite file so
# anyone can run the project without Docker installed.
DATABASES = {"default": env.db("DATABASE_URL", default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}")}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "America/Indiana/Indianapolis"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "AccessPath API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# Background jobs. Separate queues so a big PDF never blocks a quick regenerate.
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_ROUTES = {
    "apps.uploads.tasks.*": {"queue": "convert"},
    "apps.pipeline.tasks.*": {"queue": "llm"},
    "apps.exports.tasks.*": {"queue": "export"},
}

# S3. One private bucket, one folder per class (classes/<class_id>/...).
# Locally this points at MinIO from docker-compose.
S3_BUCKET = env("S3_BUCKET", default="accesspath-dev")
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default=None)
S3_REGION = env("S3_REGION", default="us-east-1")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default=None)
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default=None)
S3_PRESIGN_SECONDS = env.int("S3_PRESIGN_SECONDS", default=900)

# AI models. Changing a model is a config change, not a code change.
ANTHROPIC_API_KEY = env("ANTHROPIC_API_KEY", default=None)
LLM_STRONG_MODEL = env("LLM_STRONG_MODEL", default="claude-sonnet-5-5")
LLM_CHEAP_MODEL = env("LLM_CHEAP_MODEL", default="claude-haiku-5-5")

# Invites. How long a class invitation stays valid before it expires.
INVITE_TTL_HOURS = env.int("INVITE_TTL_HOURS", default=72)

# Uploads
MAX_UPLOAD_BYTES = env.int("MAX_UPLOAD_BYTES", default=200 * 1024 * 1024)
