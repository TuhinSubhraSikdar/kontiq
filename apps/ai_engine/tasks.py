from celery import shared_task

from .services import execute_generation


@shared_task(name="kontiq.generate_content", autoretry_for=(), acks_late=True)
def generate_content_task(task_id, token):
    return getattr(execute_generation(task_id, token), "pk", None)
