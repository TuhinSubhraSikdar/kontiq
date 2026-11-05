import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.content_library.models import GeneratedContent
from apps.content_tasks.models import ContentTask
from apps.content_types.models import ContentType
from apps.projects.models import Project

from .services import assemble_prompt, execute_generation, queue_generation
from .types import GenerationResult


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
    @patch("apps.ai_engine.services.OpenAIProvider.generate")
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
        with self.assertRaisesMessage(ValueError, "Configure OPENAI_API_KEY"):
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
    @patch("apps.ai_engine.services.OpenAIProvider.generate")
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
    @patch("apps.ai_engine.services.OpenAIProvider.generate")
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
    @patch("apps.ai_engine.services.OpenAIProvider.generate")
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
