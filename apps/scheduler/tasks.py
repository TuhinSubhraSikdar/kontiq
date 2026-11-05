from celery import shared_task

from .services import dispatch_due_tasks, recover_stale_tasks


@shared_task(name="kontiq.dispatch_due_tasks")
def dispatch_due_content_tasks():
    recover_stale_tasks()
    return dispatch_due_tasks()
