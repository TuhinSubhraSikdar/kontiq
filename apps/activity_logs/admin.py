from django.contrib import admin

from .models import ActivityLog


@admin.register(ActivityLog)
class ActivityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "event_type", "summary", "user", "project")
    list_filter = ("event_type",)
    search_fields = ("summary",)
    readonly_fields = ("user", "project", "task", "event_type", "summary", "metadata", "created_at")
