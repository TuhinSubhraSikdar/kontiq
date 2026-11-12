import tempfile
import uuid
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.urls import reverse
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.content_library.models import GeneratedContent
from apps.content_tasks.models import ContentTask
from apps.content_types.models import ContentType
from apps.projects.models import Project

from .brand_images import BrandImageAssets
from .forms import AIProviderConfigurationAdminForm
from .models import AIProviderConfiguration, AIProviderSelection
from .provider_configuration import get_runtime_provider_configuration
from .providers.openai_compatible import OpenAICompatibleProvider
from .services import assemble_prompt, execute_generation, provider_status, queue_generation
from .types import GenerationRequest, GenerationResult


TEST_ENCRYPTION_KEY = Fernet.generate_key().decode("ascii")


class GenerationServiceTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="generator")
        self.project = Project.objects.create(owner=self.user, name="Acme", description="A company")
        self.content_type = ContentType.objects.create(owner=self.user, name="Article", default_word_count=100)
        self.token = uuid.uuid4()
        self.task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="SEO basics",
            primary_keyword="SEO basics",
            target_word_count=100,
            status=ContentTask.Status.QUEUED,
            lock_token=self.token,
            lock_acquired_at=timezone.now(),
        )

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="test-model", AI_MAX_RETRIES=1)
    @patch("apps.ai_engine.provider_configuration.OpenAIProvider.generate")
    def test_execute_generation_persists_valid_result_and_is_idempotent(self, generate):
        body = "SEO basics " + " ".join(f"word{i}" for i in range(90))
        generate.return_value = GenerationResult(
            text='{"title":"SEO basics","meta_description":"A guide","slug":"seo-basics","body":"' + body + '"}',
            provider="openai",
            model="test-model",
            response_id="resp_123",
        )
        content = execute_generation(self.task.pk, self.token)
        self.assertEqual(content.provider_response_id, "resp_123")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, ContentTask.Status.COMPLETED)
        self.assertEqual(GeneratedContent.objects.count(), 1)
        self.assertIsNone(execute_generation(self.task.pk, self.token))
        self.assertEqual(GeneratedContent.objects.count(), 1)

    @override_settings(OPENAI_API_KEY="", OPENAI_MODEL="")
    def test_queue_refuses_unconfigured_provider_without_changing_state(self):
        self.task.status = ContentTask.Status.DRAFT
        self.task.lock_token = None
        self.task.save()
        with self.assertRaisesMessage(ValueError, "Configure and activate an AI provider"):
            queue_generation(self.task.pk, self.user)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, ContentTask.Status.DRAFT)

    def test_blank_requested_title_adds_ai_title_direction(self):
        self.task.title = ""
        self.task.save(update_fields=["title"])
        prompt = assemble_prompt(self.task)
        self.assertIn("No title was supplied", prompt)
        self.assertIn("Generate a unique, relevant title", prompt)
        self.assertIn(self.task.primary_keyword, prompt)

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="test-model", AI_MAX_RETRIES=1)
    @patch("apps.ai_engine.provider_configuration.OpenAIProvider.generate")
    def test_duplicate_ai_title_is_corrected_to_unique_title(self, generate):
        other_task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="Existing brief",
            primary_keyword="existing keyword",
            target_word_count=100,
        )
        GeneratedContent.objects.create(
            task=other_task,
            project=self.project,
            content_type=self.content_type,
            title="A Distinctive SEO Guide",
            slug="a-distinctive-seo-guide",
            body="Existing body",
            provider="openai",
            model_name="test-model",
        )
        self.task.title = ""
        self.task.save(update_fields=["title"])
        body = "SEO basics " + " ".join(f"word{i}" for i in range(90))
        generate.side_effect = [
            GenerationResult(
                text='{"title":"A Distinctive SEO Guide","meta_description":"A guide","slug":"duplicate","body":"'
                + body + '"}',
                provider="openai",
                model="test-model",
            ),
            GenerationResult(
                text='{"title":"A Fresh Approach to SEO Basics","meta_description":"A guide","slug":"fresh-seo-basics","body":"'
                + body + '"}',
                provider="openai",
                model="test-model",
            ),
        ]
        content = execute_generation(self.task.pk, self.token)
        self.assertEqual(content.title, "A Fresh Approach to SEO Basics")
        self.assertEqual(generate.call_count, 2)

    @override_settings(
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="test-model",
        AI_MAX_RETRIES=1,
        AI_TASK_MAX_ATTEMPTS=3,
        AI_MAX_OUTPUT_TOKENS=8000,
    )
    @patch("apps.ai_engine.provider_configuration.OpenAIProvider.generate")
    def test_provider_failure_schedules_bounded_durable_retry(self, generate):
        generate.side_effect = RuntimeError("temporary provider failure")
        with self.assertRaisesMessage(RuntimeError, "temporary provider failure"):
            execute_generation(self.task.pk, self.token)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, ContentTask.Status.SCHEDULED)
        self.assertEqual(self.task.attempt_count, 1)
        self.assertIsNotNone(self.task.scheduled_for)

    @override_settings(
        OPENAI_API_KEY="test-key",
        OPENAI_MODEL="test-model",
        AI_MAX_RETRIES=1,
        AI_MAX_OUTPUT_TOKENS=8000,
    )
    @patch("apps.ai_engine.provider_configuration.OpenAIProvider.generate")
    def test_invalid_json_uses_bounded_correction_attempt(self, generate):
        body = "SEO basics " + " ".join(f"word{i}" for i in range(90))
        generate.side_effect = [
            GenerationResult(text="not json", provider="openai", model="test-model"),
            GenerationResult(
                text='{"title":"SEO basics","meta_description":"A guide","slug":"seo-basics","body":"' + body + '"}',
                provider="openai",
                model="test-model",
            ),
        ]
        content = execute_generation(self.task.pk, self.token)
        self.assertEqual(content.slug, "seo-basics")
        self.assertEqual(generate.call_count, 2)

    @override_settings(OPENAI_API_KEY="test-key", OPENAI_MODEL="test-model", AI_MAX_RETRIES=1)
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp(prefix="kontiq-image-tests-"))
    @patch("apps.ai_engine.services.generate_brand_images")
    @patch("apps.ai_engine.provider_configuration.OpenAIProvider.generate")
    def test_generation_persists_feature_and_body_images(self, generate, generate_images):
        from PIL import Image

        logo = BytesIO()
        Image.new("RGBA", (20, 20), "#123456").save(logo, format="PNG")
        self.project.brand_color = "#123456"
        self.project.brand_logo.save("logo.png", ContentFile(logo.getvalue()), save=True)
        self.project.save()
        image = BytesIO()
        Image.new("RGB", (40, 40), "#abcdef").save(image, format="JPEG")
        generate_images.return_value = BrandImageAssets(feature=image.getvalue(), body=image.getvalue())
        body = "SEO basics " + " ".join(f"word{i}" for i in range(90))
        generate.return_value = GenerationResult(
            text='{"title":"SEO basics","meta_description":"A guide","slug":"seo-basics","body":"' + body + '"}',
            provider="openai",
            model="test-model",
        )

        content = execute_generation(self.task.pk, self.token)

        self.assertTrue(content.feature_image.name)
        self.assertTrue(content.body_image.name)
        generate_images.assert_called_once()

    @override_settings(
        OPENAI_API_KEY="",
        OPENAI_MODEL="",
        AI_CREDENTIAL_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY,
        AI_MAX_RETRIES=1,
    )
    @patch("apps.ai_engine.provider_configuration.OpenAICompatibleProvider.generate")
    def test_execute_generation_uses_active_database_provider(self, generate):
        configuration = AIProviderConfiguration(
            name="Worker Gemini",
            provider=AIProviderConfiguration.Provider.GEMINI,
            model_name="gemini-worker-model",
        )
        configuration.set_api_key("gemini-worker-secret")
        configuration.save()
        AIProviderSelection.objects.create(configuration=configuration)
        body = "SEO basics " + " ".join(f"word{i}" for i in range(90))
        generate.return_value = GenerationResult(
            text='{"title":"SEO basics","meta_description":"A guide","slug":"seo-basics","body":"'
            + body
            + '"}',
            provider="gemini",
            model="gemini-worker-model",
        )
        content = execute_generation(self.task.pk, self.token)
        self.assertEqual(content.provider, "gemini")
        self.assertEqual(content.model_name, "gemini-worker-model")
        request = generate.call_args.args[0]
        self.assertEqual(request.model, "gemini-worker-model")


@override_settings(AI_CREDENTIAL_ENCRYPTION_KEY=TEST_ENCRYPTION_KEY)
class ProviderConfigurationTests(TestCase):
    def create_configuration(self, *, name, provider, model, api_key, is_active=False):
        configuration = AIProviderConfiguration(
            name=name,
            provider=provider,
            model_name=model,
        )
        configuration.set_api_key(api_key)
        configuration.full_clean()
        configuration.save()
        if is_active:
            AIProviderSelection.objects.update_or_create(
                singleton=1, defaults={"configuration": configuration}
            )
        return configuration

    def test_api_key_is_encrypted_and_active_configuration_is_dynamic(self):
        first = self.create_configuration(
            name="Primary Gemini",
            provider=AIProviderConfiguration.Provider.GEMINI,
            model="gemini-test",
            api_key="gemini-secret-1234",
            is_active=True,
        )
        stored = AIProviderConfiguration.objects.get(pk=first.pk)
        self.assertNotIn("gemini-secret-1234", stored.encrypted_api_key)
        self.assertEqual(stored.get_api_key(), "gemini-secret-1234")
        self.assertEqual(stored.api_key_hint, "••••1234")

        second = self.create_configuration(
            name="Backup Claude",
            provider=AIProviderConfiguration.Provider.ANTHROPIC,
            model="claude-test",
            api_key="claude-secret-5678",
            is_active=True,
        )
        selection = AIProviderSelection.objects.get(singleton=1)
        self.assertEqual(selection.configuration, second)
        self.assertFalse(AIProviderSelection.objects.filter(configuration=first).exists())
        runtime = get_runtime_provider_configuration()
        self.assertEqual(runtime.provider, AIProviderConfiguration.Provider.ANTHROPIC)
        self.assertEqual(runtime.model, "claude-test")
        self.assertEqual(runtime.api_key, "claude-secret-5678")
        self.assertEqual(provider_status()["source"], "database")

    def test_admin_form_blank_key_preserves_saved_credential(self):
        configuration = self.create_configuration(
            name="Groq",
            provider=AIProviderConfiguration.Provider.GROQ,
            model="groq-model",
            api_key="groq-secret-1234",
        )
        original_ciphertext = configuration.encrypted_api_key
        form = AIProviderConfigurationAdminForm(
            data={
                "name": configuration.name,
                "provider": configuration.provider,
                "model_name": "new-groq-model",
                "api_base_url": "",
                "api_key": "",
                "make_active": "",
            },
            instance=configuration,
        )
        self.assertTrue(form.is_valid(), form.errors)
        updated = form.save()
        self.assertEqual(updated.encrypted_api_key, original_ciphertext)
        self.assertEqual(updated.get_api_key(), "groq-secret-1234")

    def test_admin_never_displays_saved_key_or_ciphertext(self):
        configuration = self.create_configuration(
            name="OpenRouter",
            provider=AIProviderConfiguration.Provider.OPENROUTER,
            model="vendor/model",
            api_key="openrouter-secret-9876",
        )
        admin_user = get_user_model().objects.create_superuser(
            username="admin", email="admin@example.com", password="password"
        )
        self.client.force_login(admin_user)
        response = self.client.get(
            reverse("admin:ai_engine_aiproviderconfiguration_change", args=[configuration.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "openrouter-secret-9876")
        self.assertNotContains(response, configuration.encrypted_api_key)
        self.assertContains(response, "••••9876")

    def test_admin_can_create_and_activate_a_provider(self):
        admin_user = get_user_model().objects.create_superuser(
            username="admin-create", email="create@example.com", password="password"
        )
        self.client.force_login(admin_user)
        response = self.client.post(
            reverse("admin:ai_engine_aiproviderconfiguration_add"),
            data={
                "name": "Admin Gemini",
                "provider": AIProviderConfiguration.Provider.GEMINI,
                "model_name": "gemini-admin-model",
                "api_base_url": "",
                "api_key": "admin-secret-2468",
                "make_active": "on",
                "_save": "Save",
            },
        )
        self.assertEqual(response.status_code, 302)
        configuration = AIProviderConfiguration.objects.get(name="Admin Gemini")
        self.assertEqual(
            AIProviderSelection.objects.get(singleton=1).configuration,
            configuration,
        )
        self.assertEqual(configuration.get_api_key(), "admin-secret-2468")

    @override_settings(AI_CREDENTIAL_ENCRYPTION_KEY="")
    def test_admin_form_reports_missing_encryption_key(self):
        form = AIProviderConfigurationAdminForm(
            data={
                "name": "Unavailable",
                "provider": AIProviderConfiguration.Provider.OPENAI,
                "model_name": "test-model",
                "api_base_url": "",
                "api_key": "secret-key",
                "make_active": "on",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("AI_CREDENTIAL_ENCRYPTION_KEY", form.errors["api_key"][0])


class OpenAICompatibleProviderTests(TestCase):
    @patch("apps.ai_engine.providers.openai_compatible.OpenAI")
    def test_chat_completion_is_mapped_to_provider_neutral_result(self, openai_client):
        client = MagicMock()
        openai_client.return_value = client
        client.chat.completions.create.return_value = SimpleNamespace(
            id="response-123",
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"title":"Test"}'))],
            usage=None,
        )
        provider = OpenAICompatibleProvider(
            name="gemini",
            api_key="secret",
            model="gemini-test",
            base_url="https://example.com/v1",
        )
        result = provider.generate(
            GenerationRequest(
                system="Return JSON.",
                prompt="Write an article.",
                model="gemini-test",
                max_output_tokens=500,
            )
        )
        self.assertEqual(result.text, '{"title":"Test"}')
        self.assertEqual(result.provider, "gemini")
        self.assertEqual(result.response_id, "response-123")
        openai_client.assert_called_once_with(
            api_key="secret",
            base_url="https://example.com/v1",
            timeout=90.0,
            max_retries=0,
        )
        client.chat.completions.create.assert_called_once_with(
            model="gemini-test",
            messages=[
                {"role": "system", "content": "Return JSON."},
                {"role": "user", "content": "Write an article."},
            ],
            max_tokens=500,
        )
