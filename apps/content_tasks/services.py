from dataclasses import dataclass

from django.db import transaction

from apps.activity_logs.services import record_activity

from .models import ContentTask


@transaction.atomic
def create_tasks_from_csv(*, owner, project, rows):
    if project.owner_id != owner.id:
        raise ValueError("Select one of your projects.")
    tasks = []
    for row in rows:
        content_type = row["content_type"]
        if content_type.owner_id != owner.id:
            raise ValueError("Every content type must belong to your account.")
        tasks.append(ContentTask(project=project, **row))
    created = ContentTask.objects.bulk_create(tasks)
    record_activity(
        user=owner,
        project=project,
        event_type="task.csv_imported",
        summary=f"Imported {len(created)} content tasks from CSV",
        metadata={"task_count": len(created)},
    )
    return created


def update_task_row(*, task, form):
    if task.status in {ContentTask.Status.QUEUED, ContentTask.Status.PROCESSING}:
        raise ValueError("A queued or processing task cannot be edited.")
    return form.save()


@dataclass(frozen=True)
class BatchQueueResult:
    queued: int
    already_active: int
    unavailable: int
    errors: tuple[str, ...]


def queue_selected_tasks(*, owner, task_ids):
    # Import here to keep task-domain services independent from provider startup.
    from apps.ai_engine.services import provider_status, queue_generation

    if not provider_status()["configured"]:
        raise ValueError("Configure OPENAI_API_KEY and OPENAI_MODEL before generating content.")

    unique_ids = []
    for task_id in task_ids:
        try:
            task_id = int(task_id)
        except (TypeError, ValueError):
            continue
        if task_id not in unique_ids:
            unique_ids.append(task_id)
    if not unique_ids:
        raise ValueError("Select at least one content row to proceed.")
    if len(unique_ids) > 100:
        raise ValueError("Proceed with no more than 100 rows at once.")

    owned_ids = set(
        ContentTask.objects.filter(pk__in=unique_ids, project__owner=owner).values_list("pk", flat=True)
    )
    queued = 0
    already_active = 0
    errors = []
    for task_id in unique_ids:
        if task_id not in owned_ids:
            continue
        try:
            _, created = queue_generation(task_id, owner)
        except (ValueError, RuntimeError) as exc:
            errors.append(str(exc))
        else:
            if created:
                queued += 1
            else:
                already_active += 1
    return BatchQueueResult(
        queued=queued,
        already_active=already_active,
        unavailable=len(unique_ids) - len(owned_ids),
        errors=tuple(dict.fromkeys(errors)),
    )
