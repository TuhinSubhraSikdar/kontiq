from dataclasses import dataclass

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from .crypto import CredentialDecryptionError
from .models import AIProviderConfiguration, AIProviderSelection
from .providers import OpenAICompatibleProvider, OpenAIProvider


@dataclass(frozen=True)
class RuntimeProviderConfiguration:
    provider: str
    name: str
    model: str
    api_key: str
    base_url: str
    source: str
    api_key_hint: str = ""

    @property
    def configured(self):
        return bool(self.provider and self.model and self.api_key)


def _database_configuration():
    selection = (
        AIProviderSelection.objects.select_related("configuration")
        .filter(singleton=1)
        .first()
    )
    configuration = selection.configuration if selection else None
    if not configuration:
        return None
    return RuntimeProviderConfiguration(
        provider=configuration.provider,
        name=configuration.get_provider_display(),
        model=configuration.model_name,
        api_key=configuration.get_api_key(),
        base_url=configuration.effective_api_base_url,
        source="database",
        api_key_hint=configuration.api_key_hint,
    )


def get_runtime_provider_configuration():
    database_configuration = _database_configuration()
    if database_configuration:
        return database_configuration
    return RuntimeProviderConfiguration(
        provider=AIProviderConfiguration.Provider.OPENAI,
        name="OpenAI",
        model=settings.OPENAI_MODEL,
        api_key=settings.OPENAI_API_KEY,
        base_url=AIProviderConfiguration.DEFAULT_BASE_URLS[
            AIProviderConfiguration.Provider.OPENAI
        ],
        source="environment",
    )


def build_active_provider():
    configuration = get_runtime_provider_configuration()
    if not configuration.configured:
        raise ImproperlyConfigured(
            "Configure an active AI provider with an API key and model before generating content."
        )
    if configuration.provider == AIProviderConfiguration.Provider.OPENAI:
        provider = OpenAIProvider(
            api_key=configuration.api_key,
            model=configuration.model,
            base_url=configuration.base_url,
        )
    else:
        provider = OpenAICompatibleProvider(
            name=configuration.provider,
            api_key=configuration.api_key,
            model=configuration.model,
            base_url=configuration.base_url,
        )
    return provider, configuration


def safe_provider_status():
    try:
        configuration = get_runtime_provider_configuration()
    except (CredentialDecryptionError, ImproperlyConfigured):
        selection = (
            AIProviderSelection.objects.select_related("configuration")
            .filter(singleton=1)
            .first()
        )
        active = selection.configuration if selection else None
        return {
            "name": active.get_provider_display() if active else "AI provider",
            "configured": False,
            "model": active.model_name if active else "",
            "source": "database" if active else "environment",
            "api_key_hint": active.api_key_hint if active else "",
            "error": "The saved API key cannot be decrypted. Check the credential encryption key.",
        }
    return {
        "name": configuration.name,
        "configured": configuration.configured,
        "model": configuration.model,
        "source": configuration.source,
        "api_key_hint": configuration.api_key_hint,
        "error": "",
    }
