"""Django settings for Kontiq.

All deployment-specific values are read from environment variables. Local
defaults are intentionally convenient, while non-debug deployments fail fast
if they retain the unsafe development secret.
"""

from pathlib import Path

import environ
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.FileAwareEnv(
    DJANGO_DEBUG=(bool, True),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    DJANGO_SECURE_HSTS_SECONDS=(int, 0),
    DATABASE_CONN_MAX_AGE=(int, 0),
    CELERY_TASK_ALWAYS_EAGER=(bool, False),
    CELERY_TASK_EAGER_PROPAGATES=(bool, True),
    AI_MAX_RETRIES=(int, 2),
    AI_TASK_MAX_ATTEMPTS=(int, 3),
    AI_TIMEOUT_SECONDS=(int, 90),
    AI_MAX_OUTPUT_TOKENS=(int, 8000),
    MAX_REFERENCE_UPLOAD_MB=(int, 10),
)

ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    environ.Env.read_env(ENV_FILE)

DEBUG = env.bool("DJANGO_DEBUG")
DEVELOPMENT_SECRET_KEY = "django-insecure-kontiq-local-development-only"
SECRET_KEY = env("DJANGO_SECRET_KEY", default=DEVELOPMENT_SECRET_KEY)
if not DEBUG and SECRET_KEY == DEVELOPMENT_SECRET_KEY:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set to a strong value when DJANGO_DEBUG=False."
    )

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"]
)
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core.apps.CoreConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.projects.apps.ProjectsConfig",
    "apps.content_types.apps.ContentTypesConfig",
    "apps.prompts.apps.PromptsConfig",
    "apps.content_tasks.apps.ContentTasksConfig",
    "apps.ai_engine.apps.AIEngineConfig",
    "apps.scheduler.apps.SchedulerConfig",
    "apps.content_library.apps.ContentLibraryConfig",
    "apps.activity_logs.apps.ActivityLogsConfig",
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

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DATABASE_CONN_MAX_AGE")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = env("DJANGO_TIME_ZONE", default="Asia/Kolkata")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "dashboard:index"
LOGOUT_REDIRECT_URL = "login"

SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT")
SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS")
SECURE_HSTS_INCLUDE_SUBDOMAINS = SECURE_HSTS_SECONDS > 0
SECURE_HSTS_PRELOAD = SECURE_HSTS_SECONDS > 0
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

REDIS_URL = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER")
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES")
CELERY_BEAT_SCHEDULE = {
    "dispatch-due-content-tasks": {
        "task": "kontiq.dispatch_due_tasks",
        "schedule": 60.0,
    }
}

OPENAI_API_KEY = env("OPENAI_API_KEY", default="")
OPENAI_MODEL = env("OPENAI_MODEL", default="")
AI_CREDENTIAL_ENCRYPTION_KEY = env("AI_CREDENTIAL_ENCRYPTION_KEY", default="")
AI_MAX_RETRIES = env.int("AI_MAX_RETRIES")
AI_TASK_MAX_ATTEMPTS = env.int("AI_TASK_MAX_ATTEMPTS")
AI_TIMEOUT_SECONDS = env.int("AI_TIMEOUT_SECONDS")
AI_MAX_OUTPUT_TOKENS = env.int("AI_MAX_OUTPUT_TOKENS")
MAX_REFERENCE_UPLOAD_MB = env.int("MAX_REFERENCE_UPLOAD_MB")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} {name}: {message}",
            "style": "{",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        }
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}
