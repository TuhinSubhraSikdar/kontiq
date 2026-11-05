"""Root URL configuration for Kontiq."""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path(
        "favicon.ico",
        RedirectView.as_view(
            url=f"{settings.STATIC_URL}images/favicon.svg", permanent=True
        ),
        name="favicon",
    ),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("foundation/", include("apps.core.urls")),
    path("projects/", include("apps.projects.urls")),
    path("prompts/", include("apps.prompts.urls")),
    path("tasks/", include("apps.content_tasks.urls")),
    path("library/", include("apps.content_library.urls")),
    path("scheduler/", include("apps.scheduler.urls")),
    path("activity/", include("apps.activity_logs.urls")),
    path("settings/ai/", include("apps.ai_engine.urls")),
    path("", include("apps.dashboard.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
