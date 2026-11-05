from urllib.parse import urlsplit

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from .crypto import decrypt_credential, encrypt_credential


class AIProviderConfiguration(models.Model):
    class Provider(models.TextChoices):
        OPENAI = "openai", "OpenAI"
        ANTHROPIC = "anthropic", "Anthropic (Claude)"
        GEMINI = "gemini", "Google Gemini"
        GROQ = "groq", "Groq"
        OPENROUTER = "openrouter", "OpenRouter"
        OPENAI_COMPATIBLE = "openai_compatible", "Custom OpenAI-compatible"

    DEFAULT_BASE_URLS = {
        Provider.OPENAI: "https://api.openai.com/v1",
        Provider.ANTHROPIC: "https://api.anthropic.com/v1/",
        Provider.GEMINI: "https://generativelanguage.googleapis.com/v1beta/openai/",
        Provider.GROQ: "https://api.groq.com/openai/v1",
        Provider.OPENROUTER: "https://openrouter.ai/api/v1",
    }

    name = models.CharField(
        max_length=120,
        unique=True,
        help_text="A private label such as Production Gemini or Backup Claude.",
    )
    provider = models.CharField(max_length=32, choices=Provider.choices)
    model_name = models.CharField(
        max_length=160,
        help_text="Enter the exact model identifier supplied by the provider.",
    )
    api_base_url = models.URLField(
        max_length=500,
        blank=True,
        help_text=(
            "Optional HTTPS override. Required only for a custom OpenAI-compatible provider."
        ),
    )
    encrypted_api_key = models.TextField(editable=False)
    api_key_hint = models.CharField(max_length=12, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "AI provider configuration"
        verbose_name_plural = "AI provider configurations"
        indexes = [models.Index(fields=["provider"])]

    def clean(self):
        super().clean()
        if self.provider == self.Provider.OPENAI_COMPATIBLE and not self.api_base_url:
            raise ValidationError(
                {"api_base_url": "Enter the HTTPS base URL for this provider."}
            )
        if self.api_base_url:
            parsed = urlsplit(self.api_base_url)
            if parsed.scheme != "https":
                raise ValidationError({"api_base_url": "Use an HTTPS API base URL."})
            if parsed.username or parsed.password or parsed.query or parsed.fragment:
                raise ValidationError(
                    {"api_base_url": "Do not include credentials, a query, or a fragment in this URL."}
                )

    @property
    def effective_api_base_url(self):
        return self.api_base_url or self.DEFAULT_BASE_URLS.get(self.provider, "")

    def set_api_key(self, api_key):
        value = api_key.strip()
        self.encrypted_api_key = encrypt_credential(value)
        self.api_key_hint = f"••••{value[-4:]}" if len(value) >= 4 else "••••"

    def get_api_key(self):
        return decrypt_credential(self.encrypted_api_key)

    def __str__(self):
        return f"{self.name} ({self.get_provider_display()} / {self.model_name})"


class AIProviderSelection(models.Model):
    singleton = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    configuration = models.OneToOneField(
        AIProviderConfiguration,
        on_delete=models.SET_NULL,
        related_name="active_selection",
        null=True,
        blank=True,
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "active AI provider selection"
        constraints = [
            models.CheckConstraint(
                condition=Q(singleton=1),
                name="ai_provider_selection_singleton",
            )
        ]

    def save(self, *args, **kwargs):
        self.singleton = 1
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.configuration) if self.configuration else "No active AI provider"
