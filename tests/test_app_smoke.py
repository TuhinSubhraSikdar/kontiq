from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.content_library.models import GeneratedContent, GeneratedContentVersion
from apps.content_tasks.models import ContentTask
from apps.content_types.models import ContentType
from apps.projects.models import Project
from apps.prompts.models import PromptTemplate


class AuthenticatedPageSmokeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="smoke", password="pass-12345")
        self.project = Project.objects.create(owner=self.user, name="Acme")
        self.content_type = ContentType.objects.create(owner=self.user, name="Article")
        self.prompt = PromptTemplate.objects.create(owner=self.user, content_type=self.content_type)
        self.task = ContentTask.objects.create(
            project=self.project, content_type=self.content_type, title="Guide", primary_keyword="guide",
            status=ContentTask.Status.COMPLETED,
        )
        self.content = GeneratedContent.objects.create(
            task=self.task, project=self.project, content_type=self.content_type, title="Guide", slug="guide",
            body="Body", body_word_count=1, provider="openai", model_name="model",
        )
        self.version = GeneratedContentVersion.objects.create(content=self.content, version=1, title="Guide", body="Body")
        self.client.force_login(self.user)

    def test_all_primary_pages_render(self):
        urls = [
            reverse("dashboard:index"), reverse("projects:list"), reverse("projects:create"),
            reverse("projects:detail", args=[self.project.pk]), reverse("projects:edit", args=[self.project.pk]),
            reverse("projects:delete", args=[self.project.pk]), reverse("prompts:list"),
            reverse("prompts:library"),
            reverse("prompts:content_type_workspace", args=[self.content_type.pk]),
            reverse("prompts:content_type_create"), reverse("prompts:content_type_edit", args=[self.content_type.pk]),
            reverse("prompts:content_type_delete", args=[self.content_type.pk]), reverse("prompts:create"),
            reverse("prompts:edit", args=[self.prompt.pk]), reverse("prompts:delete", args=[self.prompt.pk]),
            reverse("tasks:list"), reverse("tasks:create"), reverse("tasks:bulk_create"),
            reverse("tasks:detail", args=[self.task.pk]), reverse("tasks:edit", args=[self.task.pk]),
            reverse("tasks:delete", args=[self.task.pk]), reverse("library:list"),
            reverse("library:detail", args=[self.content.pk]), reverse("library:edit", args=[self.content.pk]),
            reverse("scheduler:index"), reverse("scheduler:configure", args=[self.project.pk]),
            reverse("activity_logs:list"), reverse("ai_engine:settings"),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)
