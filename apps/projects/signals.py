from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.scheduler.models import ScheduleConfiguration

from .models import Project


@receiver(post_save, sender=Project)
def ensure_schedule_configuration(sender, instance, created, **kwargs):
    if created:
        ScheduleConfiguration.objects.get_or_create(project=instance)
