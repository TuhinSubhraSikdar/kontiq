from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .services import ensure_starter_content_types


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_starter_content_types(sender, instance, created, **kwargs):
    if created:
        ensure_starter_content_types(instance)
