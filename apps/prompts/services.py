from .forms import VARIABLE_PATTERN
from .models import PromptVersion


def render_prompt(template, values):
    """Render only documented scalar variables; no template language is evaluated."""

    return VARIABLE_PATTERN.sub(lambda match: str(values.get(match.group(1), "")), template)


def update_prompt(*, prompt, cleaned_data, user):
    """Snapshot the current prompt, then apply an editor save atomically."""

    from django.db import transaction

    with transaction.atomic():
        locked = type(prompt).objects.select_for_update().get(pk=prompt.pk)
        PromptVersion.objects.create(
            prompt=locked,
            version=locked.version,
            title=locked.title,
            description=locked.description,
            category=locked.category,
            template=locked.template,
            created_by=user,
        )
        for field in ("title", "description", "content_type", "project", "category", "template", "is_active"):
            setattr(locked, field, cleaned_data[field])
        locked.version += 1
        locked.save()
    return locked


def restore_prompt_version(*, prompt, version, user):
    return update_prompt(
        prompt=prompt,
        cleaned_data={
            "title": version.title,
            "description": version.description,
            "content_type": prompt.content_type,
            "project": prompt.project,
            "category": version.category,
            "template": version.template,
            "is_active": prompt.is_active,
        },
        user=user,
    )
