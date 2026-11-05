from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class ScheduleConfiguration(models.Model):
    project = models.OneToOneField(
        "projects.Project", on_delete=models.CASCADE, related_name="schedule_configuration"
    )
    enabled = models.BooleanField(default=True)
    max_concurrent_tasks = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(10)]
    )
    retry_delay_minutes = models.PositiveIntegerField(
        default=15, validators=[MinValueValidator(1), MaxValueValidator(1440)]
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Automation for {self.project.name}"
