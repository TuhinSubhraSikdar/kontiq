import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Project, ProjectReference

TEST_MEDIA_ROOT = tempfile.mkdtemp(prefix="kontiq-project-tests-")


class ProjectWorkflowTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="owner", password="pass-12345")
        self.other = get_user_model().objects.create_user(username="other", password="pass-12345")
        self.project = Project.objects.create(owner=self.user, name="Acme")

    def test_project_routes_enforce_ownership(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse("projects:detail", args=[self.project.pk]))
        self.assertEqual(response.status_code, 404)

    def test_create_generates_owner_scoped_unique_slug(self):
        second = Project.objects.create(owner=self.user, name="Acme")
        other = Project.objects.create(owner=self.other, name="Acme")
        self.assertEqual(self.project.slug, "acme")
        self.assertEqual(second.slug, "acme-2")
        self.assertEqual(other.slug, "acme")

    @override_settings(MEDIA_ROOT=TEST_MEDIA_ROOT)
    def test_txt_reference_is_extracted_and_private(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile("notes.txt", b"Useful private context", content_type="text/plain")
        response = self.client.post(reverse("projects:reference_add", args=[self.project.pk]), {"file": upload})
        self.assertRedirects(response, reverse("projects:detail", args=[self.project.pk]))
        reference = ProjectReference.objects.get(project=self.project)
        self.assertEqual(reference.extraction_status, ProjectReference.ExtractionStatus.READY)
        self.assertEqual(reference.extracted_text, "Useful private context")
        self.client.force_login(self.other)
        denied = self.client.get(reverse("projects:reference_download", args=[self.project.pk, reference.pk]))
        self.assertEqual(denied.status_code, 404)
        Path(reference.file.path).unlink(missing_ok=True)

    def test_misleading_pdf_is_rejected(self):
        self.client.force_login(self.user)
        upload = SimpleUploadedFile("fake.pdf", b"not a pdf", content_type="application/pdf")
        response = self.client.post(reverse("projects:reference_add", args=[self.project.pk]), {"file": upload}, follow=True)
        self.assertContains(response, "valid PDF signature")
        self.assertFalse(ProjectReference.objects.exists())
