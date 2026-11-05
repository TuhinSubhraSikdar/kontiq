from django.conf import settings
from django.db import models


class ActivityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kontiq_activity"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="activity", null=True, blank=True
    )
    task = models.ForeignKey(
        "content_tasks.ContentTask", on_delete=models.CASCADE, related_name="activity", null=True, blank=True
    )
    event_type = models.CharField(max_length=80, db_index=True)
    summary = models.CharField(max_length=300)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]

    def __str__(self):
        return self.summary
