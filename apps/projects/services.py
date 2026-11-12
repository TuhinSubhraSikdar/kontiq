from pathlib import Path

from django.db import transaction
from docx import Document
from pypdf import PdfReader

from apps.activity_logs.services import record_activity

from .models import ProjectReference


def _extract_text(reference):
    extension = Path(reference.original_name).suffix.lower()
    with reference.file.open("rb") as source:
        if extension == ".txt":
            return source.read().decode("utf-8-sig")
        if extension == ".pdf":
            return "\n".join(page.extract_text() or "" for page in PdfReader(source).pages)
        if extension == ".docx":
            return "\n".join(paragraph.text for paragraph in Document(source).paragraphs)
    raise ValueError("Unsupported reference type.")


def create_reference(*, project, upload, user):
    reference = ProjectReference.objects.create(
        project=project,
        file=upload,
        original_name=Path(upload.name).name[:255],
        mime_type=(getattr(upload, "content_type", "") or "application/octet-stream")[:120],
        size=upload.size,
        checksum=upload.kontiq_checksum,
    )
    try:
        text = _extract_text(reference).strip()
        if not text:
            raise ValueError("No readable text was found in this file.")
    except Exception as exc:  # parsing libraries expose several format-specific exceptions
        reference.extraction_status = ProjectReference.ExtractionStatus.FAILED
        reference.extraction_error = str(exc)[:300]
        reference.save(update_fields=["extraction_status", "extraction_error"])
    else:
        reference.extracted_text = text
        reference.extraction_status = ProjectReference.ExtractionStatus.READY
        reference.save(update_fields=["extracted_text", "extraction_status"])
    record_activity(
        user=user,
        project=project,
        event_type="reference.uploaded",
        summary=f"Uploaded reference {reference.original_name}",
        metadata={"status": reference.extraction_status, "size": reference.size},
    )
    return reference


def delete_project_with_files(*, project):
    paths = [reference.file.name for reference in project.references.all() if reference.file]
    storage = ProjectReference._meta.get_field("file").storage
    document_paths = [
        path
        for content in project.generated_contents.all()
        for path in (content.document.name, content.feature_image.name, content.body_image.name)
        if path
    ]
    logo_path = project.brand_logo.name if project.brand_logo else ""
    document_storage = project.generated_contents.model._meta.get_field("document").storage
    with transaction.atomic():
        project.delete()
        transaction.on_commit(
            lambda: (
                [storage.delete(path) for path in paths],
                [document_storage.delete(path) for path in document_paths],
                document_storage.delete(logo_path) if logo_path else None,
            )
        )


def delete_reference_with_file(*, reference):
    path = reference.file.name
    storage = reference.file.storage
    with transaction.atomic():
        reference.delete()
        transaction.on_commit(lambda: storage.delete(path))
