from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify


class ContentType(models.Model):
    class Category(models.TextChoices):
        EDITORIAL = "editorial", "Editorial"
        SEO = "seo", "SEO content"
        PR = "pr", "Public relations"
        SOCIAL = "social", "Social"
        LOCAL = "local", "Local marketing"
        CUSTOM = "custom", "Custom"

    ICON_CHOICES = (
        ("file-text", "Article"),
        ("globe", "Web"),
        ("newspaper", "Press release"),
        ("bookmark", "Bookmark"),
        ("building", "Business"),
        ("messages", "Community"),
        ("sparkles", "AI content"),
        ("layout", "General"),
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="kontiq_content_types"
    )
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=140)
    description = models.TextField(blank=True)
    category = models.CharField(
        max_length=24, choices=Category.choices, default=Category.CUSTOM, db_index=True
    )
    icon = models.CharField(max_length=24, choices=ICON_CHOICES, default="file-text")
    color = models.CharField(
        max_length=7,
        default="#126BFF",
        validators=[RegexValidator(r"^#[0-9A-Fa-f]{6}$", "Enter a six-digit hex color.")],
    )
    custom_fields = models.JSONField(default=list, blank=True)
    is_favorite = models.BooleanField(default=False, db_index=True)
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
        indexes = [models.Index(fields=["owner", "category", "is_active"])]

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
