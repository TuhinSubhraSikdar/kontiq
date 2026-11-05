import re

from django import forms
from django.core.exceptions import ValidationError

from .models import PromptTemplate


SUPPORTED_VARIABLES = {
    "title", "primary_keyword", "secondary_keywords", "target_url", "word_count",
    "content_type", "project_name", "project_description", "audience", "brand_voice",
    "instructions", "avoid_topics", "links", "references", "task_notes",
}
VARIABLE_PATTERN = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*}}")


class PromptTemplateForm(forms.ModelForm):
    class Meta:
        model = PromptTemplate
        fields = ["content_type", "project", "template", "is_active"]
        widgets = {"template": forms.Textarea(attrs={"rows": 18, "class": "code-input"})}

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.fields["content_type"].queryset = owner.kontiq_content_types.all()
        self.fields["project"].queryset = owner.kontiq_projects.all()
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        content_type = cleaned.get("content_type")
        project = cleaned.get("project")
        if content_type and content_type.owner_id != self.owner.id:
            raise ValidationError("Select one of your content types.")
        if project and project.owner_id != self.owner.id:
            raise ValidationError("Select one of your projects.")
        return cleaned

    def clean_template(self):
        template = self.cleaned_data["template"]
        variables = set(VARIABLE_PATTERN.findall(template))
        unknown = sorted(variables - SUPPORTED_VARIABLES)
        if unknown:
            raise ValidationError(f"Unsupported variables: {', '.join(unknown)}")
        return template
