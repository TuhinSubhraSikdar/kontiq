import uuid
from pathlib import Path

from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.utils.text import get_valid_filename, slugify


def reference_upload_path(instance, filename):
    safe_name = get_valid_filename(Path(filename).name)
    return f"project_references/{instance.project.slug}/{uuid.uuid4().hex}-{safe_name}"


class Project(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kontiq_projects"
    )
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180)
    website_url = models.URLField(blank=True)
    description = models.TextField(blank=True)
    audience = models.TextField(blank=True)
    brand_voice = models.TextField(blank=True)
    instructions = models.TextField(blank=True)
    avoid_topics = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], name="unique_project_owner_slug")
        ]
        indexes = [models.Index(fields=["owner", "is_active"])]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:160] or "project"
            candidate = base
            suffix = 2
            while Project.objects.filter(owner=self.owner, slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base[:165 - len(str(suffix))]}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class ProjectLink(models.Model):
    class Category(models.TextChoices):
        WEBSITE = "website", "Website"
        SOCIAL = "social", "Social profile"
        REFERENCE = "reference", "Reference"
        INTERNAL = "internal", "Internal link"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="links")
    label = models.CharField(max_length=120)
    url = models.URLField(max_length=500)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.REFERENCE)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["category", "label"]
        indexes = [models.Index(fields=["project", "category", "is_active"])]

    def __str__(self):
        return self.label


class ProjectReference(models.Model):
    class ExtractionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="references")
    file = models.FileField(
        upload_to=reference_upload_path,
        validators=[FileExtensionValidator(["txt", "pdf", "docx"])],
    )
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    size = models.PositiveBigIntegerField()
    checksum = models.CharField(max_length=64, db_index=True)
    extracted_text = models.TextField(blank=True)
    extraction_status = models.CharField(
        max_length=12, choices=ExtractionStatus.choices, default=ExtractionStatus.PENDING
    )
    extraction_error = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.original_name
