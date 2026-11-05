from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.content_tasks.models import ContentTask
from apps.content_types.models import ContentType
from apps.projects.models import Project

from .models import ScheduleConfiguration
from .services import dispatch_due_tasks, recover_stale_tasks


class SchedulerTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="scheduler")
        self.project = Project.objects.create(owner=self.user, name="Acme")
        ScheduleConfiguration.objects.update_or_create(project=self.project, defaults={"enabled": True})
        self.content_type = ContentType.objects.create(owner=self.user, name="Article")

    @override_settings(OPENAI_API_KEY="key", OPENAI_MODEL="model")
    @patch("apps.ai_engine.tasks.generate_content_task.delay")
    def test_due_task_uses_normal_queue_workflow(self, delay):
        task = ContentTask.objects.create(
            project=self.project, content_type=self.content_type, title="Due", primary_keyword="due",
            status=ContentTask.Status.SCHEDULED, scheduled_for=timezone.now() - timedelta(minutes=1),
        )
        self.assertEqual(dispatch_due_tasks(owner=self.user), 1)
        task.refresh_from_db()
        self.assertEqual(task.status, ContentTask.Status.QUEUED)
        delay.assert_called_once()

    def test_stale_lock_recovery_is_durable(self):
        task = ContentTask.objects.create(
            project=self.project, content_type=self.content_type, title="Stale", primary_keyword="stale",
            status=ContentTask.Status.PROCESSING, lock_acquired_at=timezone.now() - timedelta(hours=2),
        )
        self.assertEqual(recover_stale_tasks(), 1)
        task.refresh_from_db()
        self.assertEqual(task.status, ContentTask.Status.FAILED)
        self.assertIn("expired", task.last_error)
