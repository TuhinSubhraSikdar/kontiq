import html
import re
from io import BytesIO

from django.core.files.base import ContentFile
from django.db import transaction
from docx import Document

from apps.activity_logs.services import record_activity

from .models import GeneratedContentVersion


def _next_version(content):
    return (content.versions.order_by("-version").values_list("version", flat=True).first() or 0) + 1


def update_content(*, content, cleaned_data, user):
    with transaction.atomic():
        locked = type(content).objects.select_for_update().get(pk=content.pk)
        GeneratedContentVersion.objects.create(
            content=locked,
            version=_next_version(locked),
            title=locked.title,
            meta_description=locked.meta_description,
            body=locked.body,
            change_note=cleaned_data.pop("change_note", "") or "Snapshot before edit",
            created_by=user,
        )
        for field in ("title", "slug", "meta_description", "body"):
            setattr(locked, field, cleaned_data[field])
        locked.body_word_count = len(re.findall(r"\b[\w'-]+\b", locked.body))
        old_document = locked.document.name
        locked.document = ""
        locked.save()
        if old_document:
            transaction.on_commit(lambda: content.document.storage.delete(old_document))
    record_activity(
        user=user,
        project=locked.project,
        task=locked.task,
        event_type="content.edited",
        summary=f"Edited {locked.title}",
    )
    return locked


def render_docx(content):
    document = Document()
    document.add_heading(content.title, level=0)
    if content.meta_description:
        paragraph = document.add_paragraph()
        paragraph.add_run("Meta description: ").bold = True
        paragraph.add_run(content.meta_description)
    for block in content.body.split("\n"):
        line = block.strip()
        if not line:
            continue
        if line.startswith("### "):
            document.add_heading(line[4:], level=3)
        elif line.startswith("## "):
            document.add_heading(line[3:], level=2)
        elif line.startswith("# "):
            document.add_heading(line[2:], level=1)
        else:
            document.add_paragraph(line)
    output = BytesIO()
    document.save(output)
    output.seek(0)
    filename = f"{content.task_id}-{content.slug}-v{_next_version(content)}.docx"
    if content.document:
        content.document.delete(save=False)
    content.document.save(filename, ContentFile(output.read()), save=True)
    return content.document


def render_html_document(content):
    paragraphs = []
    for block in content.body.split("\n"):
        line = block.strip()
        if not line:
            continue
        escaped = html.escape(line)
        if line.startswith("### "):
            paragraphs.append(f"<h3>{html.escape(line[4:])}</h3>")
        elif line.startswith("## "):
            paragraphs.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith("# "):
            paragraphs.append(f"<h1>{html.escape(line[2:])}</h1>")
        else:
            paragraphs.append(f"<p>{escaped}</p>")
    return (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        f"<title>{html.escape(content.title)}</title><meta name=\"description\" content=\"{html.escape(content.meta_description)}\">"
        "</head><body><article>" + "\n".join(paragraphs) + "</article></body></html>"
    )
