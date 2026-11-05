from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.content_types.models import ContentType
from apps.projects.models import Project

from .models import ContentTask


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
