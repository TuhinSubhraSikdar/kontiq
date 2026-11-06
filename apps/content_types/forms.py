from django import forms

from .models import ContentType


class ContentTypeForm(forms.ModelForm):
    custom_fields_input = forms.CharField(
        label="Custom fields",
        required=False,
        help_text="Optional field names, one per line. These are saved with the content type for brief planning.",
        widget=forms.Textarea(attrs={"rows": 4, "placeholder": "Call to action\nAuthor bio\nPublication name"}),
    )

    class Meta:
        model = ContentType
        fields = [
            "name", "description", "category", "icon", "color", "default_word_count",
            "requirements", "custom_fields_input", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Guest Post"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "When and how this format is used"}),
            "requirements": forms.Textarea(attrs={"rows": 5, "placeholder": "Structure, tone, links, and quality requirements"}),
            "color": forms.TextInput(attrs={"type": "color", "class": "form-control form-control-color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["custom_fields_input"].initial = "\n".join(self.instance.custom_fields or [])
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_custom_fields_input(self):
        fields = []
        for raw_name in self.cleaned_data.get("custom_fields_input", "").splitlines():
            name = " ".join(raw_name.split()).strip()
            if name and name.casefold() not in {item.casefold() for item in fields}:
                fields.append(name[:80])
        if len(fields) > 20:
            raise forms.ValidationError("Add no more than 20 custom fields.")
        return fields

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.custom_fields = self.cleaned_data.get("custom_fields_input", [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance
