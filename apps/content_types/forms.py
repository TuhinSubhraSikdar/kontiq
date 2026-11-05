from django import forms

from .models import ContentType


class ContentTypeForm(forms.ModelForm):
    class Meta:
        model = ContentType
        fields = ["name", "description", "default_word_count", "requirements", "is_active"]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "requirements": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
