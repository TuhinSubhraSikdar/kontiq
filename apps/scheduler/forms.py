from django import forms

from .models import ScheduleConfiguration


class ScheduleConfigurationForm(forms.ModelForm):
    class Meta:
        model = ScheduleConfiguration
        fields = ["enabled", "max_concurrent_tasks", "retry_delay_minutes"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
