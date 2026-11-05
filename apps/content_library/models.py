from django.conf import settings
from django.db import models


def generated_document_path(instance, filename):
    return f"generated_docs/{instance.project.slug}/{filename}"


class GeneratedContent(models.Model):
    task = models.OneToOneField(
        "content_tasks.ContentTask", on_delete=models.CASCADE, related_name="generated_content"
    )
    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="generated_contents")
    content_type = models.ForeignKey(
        "content_types.ContentType", on_delete=models.PROTECT, related_name="generated_contents"
    )
    title = models.CharField(max_length=240)
    slug = models.SlugField(max_length=240)
    meta_description = models.CharField(max_length=320, blank=True)
    body = models.TextField()
    body_word_count = models.PositiveIntegerField(default=0)
    provider = models.CharField(max_length=60)
    model_name = models.CharField(max_length=120)
    provider_response_id = models.CharField(max_length=160, blank=True)
    usage = models.JSONField(default=dict, blank=True)
    document = models.FileField(upload_to=generated_document_path, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["project", "slug"], name="unique_generated_project_slug")
        ]

    def __str__(self):
        return self.title


class GeneratedContentVersion(models.Model):
    content = models.ForeignKey(GeneratedContent, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=240)
    meta_description = models.CharField(max_length=320, blank=True)
    body = models.TextField()
    change_note = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["content", "version"], name="unique_generated_content_version")
        ]

    def __str__(self):
        return f"{self.content.title} v{self.version}"
