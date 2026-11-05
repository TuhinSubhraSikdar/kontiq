"""Read-only dashboard services.

Phase 1 has no business-domain models yet, so this service reports only live
foundation readiness. Domain totals will be added when their owning apps and
models are implemented; no placeholder statistics are returned here.
"""

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from django.apps import apps
from django.conf import settings
from django.db import DatabaseError, connection


@dataclass(frozen=True)
class HealthCheck:
    label: str
    value: str
    detail: str
    tone: str
    icon: str


@dataclass(frozen=True)
class ModuleStatus:
    label: str
    description: str
    app_path: str
    phase: str

    @property
    def is_available(self) -> bool:
        return apps.is_installed(self.app_path)

    @property
    def status_label(self) -> str:
        return "Available" if self.is_available else "Planned"

    @property
    def status_tone(self) -> str:
        return "success" if self.is_available else "neutral"


@dataclass(frozen=True)
class DashboardSnapshot:
    health_checks: tuple[HealthCheck, ...]
    modules: tuple[ModuleStatus, ...]
    metrics: tuple[dict, ...] = ()
    recent_activity: tuple = ()


MODULES = (
    ModuleStatus(
        label="Dashboard",
        description="Workspace overview and operational readiness.",
        app_path="apps.dashboard",
        phase="Phase 1",
    ),
    ModuleStatus(
        label="Projects",
        description="Business context, links, instructions, and references.",
        app_path="apps.projects",
        phase="Phase 2",
    ),
    ModuleStatus(
        label="Prompt Manager",
        description="Content types, prompt templates, overrides, and previews.",
        app_path="apps.prompts",
        phase="Phase 3",
    ),
    ModuleStatus(
        label="Content Tasks",
        description="Task creation, bulk input, filtering, and scheduling.",
        app_path="apps.content_tasks",
        phase="Phase 4",
    ),
    ModuleStatus(
        label="AI Generation",
        description="Provider adapters, validation, correction, and storage.",
        app_path="apps.ai_engine",
        phase="Phase 5",
    ),
    ModuleStatus(
        label="Automation",
        description="Durable dispatch, retries, queue visibility, and recovery.",
        app_path="apps.scheduler",
        phase="Phase 6",
    ),
    ModuleStatus(
        label="Content Library",
        description="Editing, versions, previews, and document downloads.",
        app_path="apps.content_library",
        phase="Phase 7",
    ),
)


def _database_health() -> HealthCheck:
    engine = connection.settings_dict["ENGINE"].rsplit(".", maxsplit=1)[-1]
    engine_label = {"sqlite3": "SQLite", "postgresql": "PostgreSQL"}.get(
        engine, engine.replace("_", " ").title()
    )
    try:
        connection.ensure_connection()
    except DatabaseError:
        return HealthCheck(
            label="Database",
            value="Unavailable",
            detail=f"{engine_label} could not be reached.",
            tone="danger",
            icon="database",
        )
    return HealthCheck(
        label="Database",
        value="Connected",
        detail=f"{engine_label} is responding normally.",
        tone="success",
        icon="database",
    )


def _storage_health() -> HealthCheck:
    media_root = Path(settings.MEDIA_ROOT)
    required_directories = (
        media_root / "project_references",
        media_root / "generated_docs",
    )
    ready = media_root.is_dir() and all(path.is_dir() for path in required_directories)
    return HealthCheck(
        label="Local storage",
        value="Ready" if ready else "Needs attention",
        detail=(
            "Reference and document directories are available."
            if ready
            else "One or more configured media directories are missing."
        ),
        tone="success" if ready else "warning",
        icon="folder",
    )


def _queue_health() -> HealthCheck:
    broker_url = settings.CELERY_BROKER_URL
    scheme = urlsplit(broker_url).scheme.lower()
    is_redis = scheme in {"redis", "rediss"}
    return HealthCheck(
        label="Background queue",
        value="Configured" if is_redis else "Check configuration",
        detail=(
            "Redis transport is configured; connectivity is checked by workers."
            if is_redis
            else "Celery is not currently configured with a Redis transport."
        ),
        tone="info" if is_redis else "warning",
        icon="queue",
    )


def get_dashboard_snapshot(user=None) -> DashboardSnapshot:
    """Return current system readiness without caching the result."""

    metrics = ()
    recent_activity = ()
    if user and user.is_authenticated:
        from apps.activity_logs.models import ActivityLog
        from apps.content_library.models import GeneratedContent
        from apps.content_tasks.models import ContentTask
        from apps.projects.models import Project

        task_queryset = ContentTask.objects.filter(project__owner=user)
        metrics = (
            {"label": "Projects", "value": Project.objects.filter(owner=user).count(), "detail": "Isolated workspaces"},
            {"label": "Open tasks", "value": task_queryset.exclude(status=ContentTask.Status.COMPLETED).count(), "detail": "Draft through processing"},
            {"label": "Completed", "value": GeneratedContent.objects.filter(project__owner=user).count(), "detail": "Library articles"},
            {"label": "Failed", "value": task_queryset.filter(status=ContentTask.Status.FAILED).count(), "detail": "Needs attention"},
        )
        recent_activity = tuple(ActivityLog.objects.filter(user=user).select_related("project")[:6])
    return DashboardSnapshot(
        health_checks=(_database_health(), _storage_health(), _queue_health()),
        modules=MODULES,
        metrics=metrics,
        recent_activity=recent_activity,
    )
