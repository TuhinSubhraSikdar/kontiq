import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ContentTask(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SCHEDULED = "scheduled", "Scheduled"
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="content_tasks")
    content_type = models.ForeignKey(
        "content_types.ContentType", on_delete=models.PROTECT, related_name="content_tasks"
    )
    title = models.CharField(max_length=240, blank=True)
    primary_keyword = models.CharField(max_length=180)
    secondary_keywords = models.TextField(blank=True)
    target_url = models.URLField(blank=True)
    notes = models.TextField(blank=True)
    target_word_count = models.PositiveIntegerField(
        default=1200, validators=[MinValueValidator(100), MaxValueValidator(10000)]
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT, db_index=True)
    scheduled_for = models.DateTimeField(null=True, blank=True, db_index=True)
    lock_token = models.UUIDField(null=True, blank=True, editable=False)
    lock_acquired_at = models.DateTimeField(null=True, blank=True, editable=False)
    attempt_count = models.PositiveIntegerField(default=0, editable=False)
    last_error = models.CharField(max_length=500, blank=True, editable=False)
    idempotency_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"]),
            models.Index(fields=["status", "scheduled_for"]),
        ]

    @property
    def status_tone(self):
        return {
            self.Status.COMPLETED: "success",
            self.Status.FAILED: "danger",
            self.Status.PROCESSING: "info",
            self.Status.QUEUED: "info",
            self.Status.SCHEDULED: "warning",
        }.get(self.status, "neutral")

    @property
    def display_title(self):
        return self.title or self.primary_keyword

    def __str__(self):
        return self.display_title
