import hashlib
from pathlib import Path

from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError

from .models import Project, ProjectLink, ProjectReference


class StyledModelForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ProjectForm(StyledModelForm):
    class Meta:
        model = Project
        fields = [
            "name", "website_url", "description", "audience", "brand_voice",
            "instructions", "avoid_topics", "is_active",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "audience": forms.Textarea(attrs={"rows": 3}),
            "brand_voice": forms.Textarea(attrs={"rows": 3}),
            "instructions": forms.Textarea(attrs={"rows": 4}),
            "avoid_topics": forms.Textarea(attrs={"rows": 3}),
        }


class ProjectLinkForm(StyledModelForm):
    class Meta:
        model = ProjectLink
        fields = ["label", "url", "category", "is_active"]


class ProjectReferenceForm(forms.ModelForm):
    class Meta:
        model = ProjectReference
        fields = ["file"]
        widgets = {"file": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".txt,.pdf,.docx"})}

    def __init__(self, *args, project, **kwargs):
        self.project = project
        super().__init__(*args, **kwargs)

    def clean_file(self):
        upload = self.cleaned_data["file"]
        max_bytes = settings.MAX_REFERENCE_UPLOAD_MB * 1024 * 1024
        if upload.size > max_bytes:
            raise ValidationError(f"Files must be {settings.MAX_REFERENCE_UPLOAD_MB} MB or smaller.")
        extension = Path(upload.name).suffix.lower()
        if extension not in {".txt", ".pdf", ".docx"}:
            raise ValidationError("Upload a TXT, PDF, or DOCX file.")
        header = upload.read(8)
        upload.seek(0)
        if extension == ".pdf" and not header.startswith(b"%PDF-"):
            raise ValidationError("This file does not contain a valid PDF signature.")
        if extension == ".docx" and not header.startswith(b"PK"):
            raise ValidationError("This file does not contain a valid DOCX signature.")
        digest = hashlib.sha256()
        for chunk in upload.chunks():
            digest.update(chunk)
        upload.seek(0)
        checksum = digest.hexdigest()
        if self.project.references.filter(checksum=checksum).exists():
            raise ValidationError("This file has already been uploaded to the project.")
        upload.kontiq_checksum = checksum
        return upload
