from django import forms

from .models import GeneratedContent


class GeneratedContentForm(forms.ModelForm):
    change_note = forms.CharField(max_length=240, required=False)

    class Meta:
        model = GeneratedContent
        fields = ["title", "slug", "meta_description", "body"]
        widgets = {"body": forms.Textarea(attrs={"rows": 24, "class": "code-input"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
