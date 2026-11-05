from django.conf import settings
from django.db import models
from django.db.models import Q


DEFAULT_PROMPT = """Write a comprehensive {{ content_type }} about {{ title }}.
Primary keyword: {{ primary_keyword }}
Target length: {{ word_count }} words.
Follow the supplied project context and return valid JSON with keys: title, meta_description, slug, and body."""


class PromptTemplate(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kontiq_prompts"
    )
    content_type = models.ForeignKey(
        "content_types.ContentType", on_delete=models.CASCADE, related_name="prompt_templates"
    )
    project = models.ForeignKey(
        "projects.Project", on_delete=models.CASCADE, related_name="prompt_overrides", null=True, blank=True
    )
    template = models.TextField(default=DEFAULT_PROMPT)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["content_type__name", "project__name"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "content_type"],
                condition=Q(project__isnull=True),
                name="unique_default_prompt_per_owner_type",
            ),
            models.UniqueConstraint(
                fields=["project", "content_type"],
                condition=Q(project__isnull=False),
                name="unique_project_prompt_per_type",
            ),
        ]

    def __str__(self):
        scope = self.project.name if self.project else "Default"
        return f"{self.content_type.name} — {scope}"
