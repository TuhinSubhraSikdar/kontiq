from .models import ActivityLog


def record_activity(*, user, event_type, summary, project=None, task=None, metadata=None):
    """Persist a safe event. Callers must never pass prompts, provider payloads, or secrets."""

    return ActivityLog.objects.create(
        user=user,
        project=project,
        task=task,
        event_type=event_type,
        summary=summary[:300],
        metadata=metadata or {},
    )
