from django.contrib import admin

from .models import ContentTask


@admin.register(ContentTask)
class ContentTaskAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "status", "scheduled_for", "attempt_count")
    list_filter = ("status", "project")
    search_fields = ("title", "primary_keyword")
    readonly_fields = ("lock_token", "lock_acquired_at", "attempt_count", "last_error", "idempotency_key")
