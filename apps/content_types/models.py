from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.text import slugify


class ContentType(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kontiq_content_types"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    default_word_count = models.PositiveIntegerField(
        default=1200, validators=[MinValueValidator(100), MaxValueValidator(10000)]
    )
    requirements = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "slug"], name="unique_content_type_owner_slug")
        ]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:120] or "content-type"
            candidate = base
            suffix = 2
            while ContentType.objects.filter(owner=self.owner, slug=candidate).exclude(pk=self.pk).exists():
                candidate = f"{base[:125 - len(str(suffix))]}-{suffix}"
                suffix += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name
