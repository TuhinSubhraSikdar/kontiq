import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from docx import Document
from PIL import Image

from apps.content_tasks.models import ContentTask
from apps.content_types.models import ContentType
from apps.projects.models import Project

from .models import GeneratedContent, GeneratedContentVersion

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="kontiq-library-tests-")


class ContentLibraryTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="editor", password="pass-12345")
        self.project = Project.objects.create(owner=self.user, name="Acme")
        self.content_type = ContentType.objects.create(owner=self.user, name="Article")
        self.task = ContentTask.objects.create(
            project=self.project, content_type=self.content_type, title="Guide", primary_keyword="guide",
            status=ContentTask.Status.COMPLETED,
        )
        self.content = GeneratedContent.objects.create(
            task=self.task, project=self.project, content_type=self.content_type,
            title="Guide", slug="guide", meta_description="Description", body="Safe body",
            body_word_count=2, provider="openai", model_name="model",
        )
        GeneratedContentVersion.objects.create(content=self.content, version=1, title="Guide", body="Safe body")
        self.client.force_login(self.user)

    def test_edit_preserves_previous_version(self):
        response = self.client.post(reverse("library:edit", args=[self.content.pk]), {
            "title": "Updated guide", "slug": "guide", "meta_description": "Updated", "body": "New body text", "change_note": "Editorial pass",
        })
        self.assertRedirects(response, reverse("library:detail", args=[self.content.pk]))
        self.assertEqual(self.content.versions.count(), 2)
        self.content.refresh_from_db()
        self.assertEqual(self.content.title, "Updated guide")

    def test_html_download_escapes_untrusted_body(self):
        self.content.body = '<script>alert("x")</script>'
        self.content.save()
        response = self.client.get(reverse("library:html_download", args=[self.content.pk]))
        self.assertContains(response, "&lt;script&gt;")
        self.assertNotContains(response, '<script>alert("x")</script>')

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_docx_download_is_generated_privately(self):
        response = self.client.get(reverse("library:docx_download", args=[self.content.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        self.content.refresh_from_db()
        self.content.document.delete(save=False)

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_docx_embeds_generated_feature_and_body_images(self):
        image = BytesIO()
        Image.new("RGB", (40, 40), "#123456").save(image, format="JPEG")
        self.content.feature_image.save("feature.jpg", ContentFile(image.getvalue()), save=True)
        self.content.body_image.save("body.jpg", ContentFile(image.getvalue()), save=True)

        response = self.client.get(reverse("library:docx_download", args=[self.content.pk]))

        document = Document(BytesIO(b"".join(response.streaming_content)))
        self.assertEqual(len(document.inline_shapes), 2)

    def test_other_user_cannot_download_content(self):
        self.client.force_login(get_user_model().objects.create_user(username="other-editor"))
        self.assertEqual(self.client.get(reverse("library:html_download", args=[self.content.pk])).status_code, 404)
