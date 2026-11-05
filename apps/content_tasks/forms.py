import csv
from io import StringIO

from django import forms
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.utils import timezone

from .models import ContentTask


class ContentTaskForm(forms.ModelForm):
    class Meta:
        model = ContentTask
        fields = [
            "project", "content_type", "title", "primary_keyword", "secondary_keywords",
            "target_url", "target_word_count", "notes", "scheduled_for",
        ]
        widgets = {
            "notes": forms.Textarea(attrs={"rows": 4}),
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}, format="%Y-%m-%dT%H:%M"),
        }

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.fields["project"].queryset = owner.kontiq_projects.filter(is_active=True)
        self.fields["content_type"].queryset = owner.kontiq_content_types.filter(is_active=True)
        self.fields["scheduled_for"].input_formats = ["%Y-%m-%dT%H:%M"]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_scheduled_for(self):
        value = self.cleaned_data.get("scheduled_for")
        if value and value <= timezone.now():
            raise ValidationError("Choose a future date and time.")
        return value

    def clean(self):
        cleaned = super().clean()
        project = cleaned.get("project")
        content_type = cleaned.get("content_type")
        if project and project.owner_id != self.owner.id:
            raise ValidationError("Select one of your projects.")
        if content_type and content_type.owner_id != self.owner.id:
            raise ValidationError("Select one of your content types.")
        return cleaned


class BulkTaskForm(forms.Form):
    project = forms.ModelChoiceField(queryset=None)
    content_type = forms.ModelChoiceField(queryset=None)
    titles = forms.CharField(
        widget=forms.Textarea(attrs={"rows": 10}),
        help_text="One title per line. Use Title | primary keyword to set a different keyword.",
    )
    target_word_count = forms.IntegerField(min_value=100, max_value=10000, initial=1200)

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["project"].queryset = owner.kontiq_projects.filter(is_active=True)
        self.fields["content_type"].queryset = owner.kontiq_content_types.filter(is_active=True)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_titles(self):
        rows = [row.strip() for row in self.cleaned_data["titles"].splitlines() if row.strip()]
        if not rows:
            raise ValidationError("Enter at least one title.")
        if len(rows) > 100:
            raise ValidationError("Create no more than 100 tasks at once.")
        for row in rows:
            if len(row.split("|", 1)[0].strip()) > 240:
                raise ValidationError("Every title must be 240 characters or fewer.")
        return rows


class TaskRowUpdateForm(forms.ModelForm):
    class Meta:
        model = ContentTask
        fields = ["primary_keyword", "target_url", "content_type"]

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["content_type"].queryset = owner.kontiq_content_types.filter(is_active=True)


class CSVTaskUploadForm(forms.Form):
    MAX_FILE_BYTES = 2 * 1024 * 1024
    MAX_ROWS = 100
    HEADER_ALIASES = {
        "keyword": {"keyword", "keywords", "primary keyword", "topic"},
        "landing_page": {"landing page", "landing url", "target url", "url"},
        "content_type": {"type", "content type", "type of content"},
        "title": {"title", "content title"},
        "word_count": {"word count", "target word count", "words"},
    }

    project = forms.ModelChoiceField(queryset=None)
    default_content_type = forms.ModelChoiceField(
        queryset=None,
        required=False,
        help_text="Used when a CSV row has no Type value.",
    )
    csv_file = forms.FileField(
        label="CSV file",
        help_text="Required column: Keyword. Optional: Landing Page, Type, Title, Word Count. Maximum 100 rows.",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,text/csv"}),
    )

    def __init__(self, *args, owner, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner
        self.parsed_rows = []
        self.fields["project"].queryset = owner.kontiq_projects.filter(is_active=True)
        self.fields["default_content_type"].queryset = owner.kontiq_content_types.filter(is_active=True)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    @staticmethod
    def _normalise_header(value):
        return " ".join((value or "").strip().casefold().replace("_", " ").replace("-", " ").split())

    def _column_map(self, fieldnames):
        normalised = {self._normalise_header(name): name for name in (fieldnames or [])}
        return {
            canonical: next((normalised[name] for name in aliases if name in normalised), None)
            for canonical, aliases in self.HEADER_ALIASES.items()
        }

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if not upload.name.lower().endswith(".csv"):
            raise ValidationError("Upload a .csv file.")
        if upload.size > self.MAX_FILE_BYTES:
            raise ValidationError("CSV files must be 2 MB or smaller.")
        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise ValidationError("Save the CSV with UTF-8 encoding and try again.") from exc
        finally:
            upload.seek(0)
        if "\x00" in text:
            raise ValidationError("The uploaded file is not a valid text CSV.")
        upload.kontiq_csv_text = text
        return upload

    def clean(self):
        cleaned = super().clean()
        upload = cleaned.get("csv_file")
        if not upload:
            return cleaned

        try:
            reader = csv.DictReader(StringIO(upload.kontiq_csv_text))
        except csv.Error as exc:
            raise ValidationError("The CSV header could not be read.") from exc
        columns = self._column_map(reader.fieldnames)
        if not columns["keyword"]:
            raise ValidationError("The CSV must include a Keyword column.")

        content_types = list(self.owner.kontiq_content_types.filter(is_active=True))
        type_lookup = {}
        for content_type in content_types:
            type_lookup[content_type.name.strip().casefold()] = content_type
            type_lookup[content_type.slug.strip().casefold()] = content_type
        default_type = cleaned.get("default_content_type")
        url_validator = URLValidator(schemes=["http", "https"])
        errors = []
        parsed_rows = []

        try:
            csv_rows = list(reader)
        except csv.Error as exc:
            raise ValidationError("The CSV contains malformed rows.") from exc

        for row_number, row in enumerate(csv_rows, start=2):
            if None in row:
                errors.append(f"Row {row_number}: contains more values than the header.")
                continue
            values = {key: (row.get(column, "") if column else "").strip() for key, column in columns.items()}
            if not any(values.values()):
                continue
            keyword = values["keyword"]
            title = values["title"] or keyword
            if not keyword:
                errors.append(f"Row {row_number}: Keyword is required.")
                continue
            if len(keyword) > 180:
                errors.append(f"Row {row_number}: Keyword must be 180 characters or fewer.")
            if len(title) > 240:
                errors.append(f"Row {row_number}: Title must be 240 characters or fewer.")

            target_url = values["landing_page"]
            if target_url:
                try:
                    url_validator(target_url)
                except ValidationError:
                    errors.append(f"Row {row_number}: Landing Page must be a valid http or https URL.")

            content_type = default_type
            if values["content_type"]:
                content_type = type_lookup.get(values["content_type"].casefold())
                if not content_type:
                    errors.append(
                        f'Row {row_number}: Type "{values["content_type"]}" does not match an active content type.'
                    )
            if not content_type:
                errors.append(f"Row {row_number}: add a Type value or choose a default content type.")

            word_count = content_type.default_word_count if content_type else 1200
            if values["word_count"]:
                try:
                    word_count = int(values["word_count"])
                except ValueError:
                    errors.append(f"Row {row_number}: Word Count must be a whole number.")
                else:
                    if not 100 <= word_count <= 10000:
                        errors.append(f"Row {row_number}: Word Count must be between 100 and 10000.")

            parsed_rows.append({
                "title": title,
                "primary_keyword": keyword,
                "target_url": target_url,
                "content_type": content_type,
                "target_word_count": word_count,
            })

        if not parsed_rows:
            errors.append("The CSV does not contain any task rows.")
        if len(parsed_rows) > self.MAX_ROWS:
            errors.append(f"Import no more than {self.MAX_ROWS} rows at once.")
        if errors:
            raise ValidationError(errors[:25])
        self.parsed_rows = parsed_rows
        return cleaned
