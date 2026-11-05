from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.ai_engine.services import queue_generation
from apps.content_tasks.models import ContentTask


def dispatch_due_tasks(*, owner=None, limit=50):
    queryset = ContentTask.objects.filter(
        status=ContentTask.Status.SCHEDULED,
        scheduled_for__lte=timezone.now(),
        project__schedule_configuration__enabled=True,
    ).select_related("project__owner")
    if owner is not None:
        queryset = queryset.filter(project__owner=owner)
    queued = 0
    for task in queryset.order_by("scheduled_for")[:limit]:
        active = ContentTask.objects.filter(
            project=task.project,
            status__in=[ContentTask.Status.QUEUED, ContentTask.Status.PROCESSING],
        ).count()
        if active >= task.project.schedule_configuration.max_concurrent_tasks:
            continue
        try:
            _, created = queue_generation(task.pk, task.project.owner)
        except (RuntimeError, ValueError):
            continue
        queued += int(created)
    return queued


def recover_stale_tasks(*, minutes=30):
    cutoff = timezone.now() - timedelta(minutes=minutes)
    with transaction.atomic():
        tasks = list(
            ContentTask.objects.select_for_update().filter(
                status__in=[ContentTask.Status.QUEUED, ContentTask.Status.PROCESSING],
                lock_acquired_at__lt=cutoff,
            )
        )
        for task in tasks:
            task.status = ContentTask.Status.FAILED
            task.last_error = "The generation lock expired and was recovered."
            task.lock_token = None
            task.lock_acquired_at = None
            task.save(update_fields=["status", "last_error", "lock_token", "lock_acquired_at", "updated_at"])
    return len(tasks)
