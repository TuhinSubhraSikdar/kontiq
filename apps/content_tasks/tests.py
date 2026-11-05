from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from apps.content_library.models import GeneratedContent
from apps.content_types.models import ContentType
from apps.projects.models import Project

from .models import ContentTask
from .services import BatchQueueResult, queue_selected_tasks


class ContentTaskWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="task-owner", password="pass-12345")
        self.project = Project.objects.create(owner=self.user, name="Acme")
        self.content_type = ContentType.objects.create(owner=self.user, name="Article")
        self.client.force_login(self.user)

    def test_create_task(self):
        response = self.client.post(reverse("tasks:create"), {
            "project": self.project.pk,
            "content_type": self.content_type.pk,
            "title": "An SEO guide",
            "primary_keyword": "SEO guide",
            "target_word_count": 800,
        })
        task = ContentTask.objects.get()
        self.assertRedirects(response, reverse("tasks:detail", args=[task.pk]))
        self.assertEqual(task.status, ContentTask.Status.DRAFT)

    def test_create_task_allows_ai_generated_title(self):
        response = self.client.post(reverse("tasks:create"), {
            "project": self.project.pk,
            "content_type": self.content_type.pk,
            "title": "",
            "primary_keyword": "AI content planning",
            "target_word_count": 800,
        })
        task = ContentTask.objects.get()
        self.assertRedirects(response, reverse("tasks:detail", args=[task.pk]))
        self.assertEqual(task.title, "")
        self.assertEqual(task.display_title, "AI content planning")

    def test_bulk_create_parses_optional_keyword(self):
        response = self.client.post(reverse("tasks:bulk_create"), {
            "project": self.project.pk,
            "content_type": self.content_type.pk,
            "titles": "First title | first keyword\nSecond title",
            "target_word_count": 500,
        })
        self.assertRedirects(response, reverse("tasks:list"))
        self.assertEqual(ContentTask.objects.count(), 2)
        self.assertEqual(ContentTask.objects.get(title="First title").primary_keyword, "first keyword")

    def test_other_users_task_is_not_visible(self):
        task = ContentTask.objects.create(project=self.project, content_type=self.content_type, title="Private", primary_keyword="private")
        other = get_user_model().objects.create_user(username="intruder")
        self.client.force_login(other)
        self.assertEqual(self.client.get(reverse("tasks:detail", args=[task.pk])).status_code, 404)

    def test_csv_import_creates_reviewable_rows_without_generating(self):
        video = ContentType.objects.create(owner=self.user, name="Explainer Video", default_word_count=700)
        upload = SimpleUploadedFile(
            "content.csv",
            b"Keyword,Landing Page,Type\nmortgage lawyer,https://example.com/legal,Article\n"
            b"camping chair,https://example.com/chairs,Explainer Video\n",
            content_type="text/csv",
        )
        response = self.client.post(reverse("tasks:csv_import"), {
            "project": self.project.pk,
            "default_content_type": "",
            "csv_file": upload,
        })
        self.assertRedirects(response, reverse("tasks:list"))
        self.assertEqual(ContentTask.objects.count(), 2)
        imported = ContentTask.objects.get(primary_keyword="camping chair")
        self.assertEqual(imported.content_type, video)
        self.assertEqual(imported.target_url, "https://example.com/chairs")
        self.assertEqual(imported.target_word_count, 700)
        self.assertEqual(imported.status, ContentTask.Status.DRAFT)
        self.assertEqual(imported.title, "")

    def test_csv_import_reports_unknown_content_type(self):
        upload = SimpleUploadedFile(
            "content.csv",
            b"Keyword,Landing Page,Type\nkeyword,https://example.com/,Unknown Type\n",
            content_type="text/csv",
        )
        response = self.client.post(reverse("tasks:csv_import"), {
            "project": self.project.pk,
            "default_content_type": "",
            "csv_file": upload,
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "does not match an active content type")
        self.assertNotContains(response, "add a Type value or choose a default content type")
        self.assertFalse(ContentTask.objects.exists())

    def test_csv_import_matches_content_type_without_spacing_or_punctuation(self):
        upload = SimpleUploadedFile(
            "content.csv",
            b"Keyword,Landing Page,Type\nexample keyword,https://example.com/,Web2.0\n",
            content_type="text/csv",
        )
        response = self.client.post(reverse("tasks:csv_import"), {
            "project": self.project.pk,
            "default_content_type": "",
            "csv_file": upload,
        })
        self.assertRedirects(response, reverse("tasks:list"))
        task = ContentTask.objects.get(primary_keyword="example keyword")
        self.assertEqual(task.content_type.slug, "web-20")

    def test_csv_import_requires_keyword_header(self):
        upload = SimpleUploadedFile(
            "content.csv",
            b"Landing Page,Type\nhttps://example.com/,Article\n",
            content_type="text/csv",
        )
        response = self.client.post(reverse("tasks:csv_import"), {
            "project": self.project.pk,
            "default_content_type": self.content_type.pk,
            "csv_file": upload,
        })
        self.assertContains(response, "must include a Keyword column")
        self.assertFalse(ContentTask.objects.exists())

    def test_quick_update_changes_sheet_fields(self):
        task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="Original topic",
            primary_keyword="original keyword",
        )
        video = ContentType.objects.create(owner=self.user, name="Video")
        response = self.client.post(reverse("tasks:quick_update", args=[task.pk]), {
            "primary_keyword": "updated keyword",
            "target_url": "https://example.com/updated",
            "content_type": video.pk,
        })
        self.assertRedirects(response, reverse("tasks:list"))
        task.refresh_from_db()
        self.assertEqual(task.primary_keyword, "updated keyword")
        self.assertEqual(task.target_url, "https://example.com/updated")
        self.assertEqual(task.content_type, video)

    def test_quick_update_refuses_processing_row(self):
        task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="Busy topic",
            primary_keyword="original",
            status=ContentTask.Status.PROCESSING,
        )
        self.client.post(reverse("tasks:quick_update", args=[task.pk]), {
            "primary_keyword": "changed",
            "target_url": "",
            "content_type": self.content_type.pk,
        })
        task.refresh_from_db()
        self.assertEqual(task.primary_keyword, "original")

    @patch("apps.content_tasks.views.queue_selected_tasks")
    def test_proceed_selected_queues_chosen_rows(self, queue_selected):
        task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="Chosen topic",
            primary_keyword="chosen",
        )
        queue_selected.return_value = BatchQueueResult(queued=1, already_active=0, unavailable=0, errors=())
        response = self.client.post(reverse("tasks:proceed_selected"), {"task_ids": [task.pk]})
        self.assertRedirects(response, reverse("tasks:list"))
        queue_selected.assert_called_once_with(owner=self.user, task_ids=[str(task.pk)])

    @patch("apps.ai_engine.services.queue_generation")
    @patch("apps.ai_engine.services.provider_status", return_value={"configured": True})
    def test_batch_queue_service_ignores_another_users_rows(self, _provider_status, queue_generation):
        own_task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="Own topic",
            primary_keyword="own",
        )
        other = get_user_model().objects.create_user(username="other-owner")
        other_project = Project.objects.create(owner=other, name="Other")
        other_type = ContentType.objects.create(owner=other, name="Other article")
        other_task = ContentTask.objects.create(
            project=other_project,
            content_type=other_type,
            title="Other topic",
            primary_keyword="other",
        )
        queue_generation.return_value = (own_task, True)
        result = queue_selected_tasks(owner=self.user, task_ids=[own_task.pk, other_task.pk])
        self.assertEqual(result.queued, 1)
        self.assertEqual(result.unavailable, 1)
        queue_generation.assert_called_once_with(own_task.pk, self.user)

    def test_queue_list_renders_spreadsheet_controls(self):
        pending_task = ContentTask.objects.create(
            project=self.project,
            content_type=self.content_type,
            title="Sheet topic",
            primary_keyword="sheet keyword",
            target_url="https://example.com/page",
        )
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Proceed with selected")
        self.assertContains(response, "sheet keyword")
        self.assertContains(response, "https://example.com/page")
        self.assertContains(response, "Not generated")

        pending_task.status = ContentTask.Status.COMPLETED
        pending_task.save(update_fields=["status"])
        content = GeneratedContent.objects.create(
            task=pending_task,
            project=self.project,
            content_type=self.content_type,
            title="Generated sheet topic",
            slug="generated-sheet-topic",
            body="Generated body",
            provider="openai",
            model_name="test-model",
        )
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, reverse("library:detail", args=[content.pk]))
        self.assertContains(response, "Open document")

    def test_queue_list_offers_downloadable_example_csv(self):
        response = self.client.get(reverse("tasks:list"))
        self.assertContains(response, "Example CSV")
        self.assertContains(response, "/static/examples/content-tasks-example.csv")
        self.assertContains(response, "download")
