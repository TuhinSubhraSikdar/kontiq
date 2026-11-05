from django.conf import settings
from django.db import migrations


STARTER_CONTENT_TYPES = (
    (
        "Web 2.0",
        "web-20",
        "Supporting content for Web 2.0 publishing platforms.",
        700,
        "Write useful, self-contained content with a natural contextual reference to the target URL.",
    ),
    (
        "Blog Posting",
        "blog-posting",
        "Long-form website or guest blog content.",
        1200,
        "Use a clear introduction, descriptive headings, practical detail, and a concise conclusion.",
    ),
    (
        "PR Submission",
        "pr-submission",
        "Press-release style announcements for submission platforms.",
        600,
        "Use a factual news angle, headline, opening summary, supporting details, and a company boilerplate.",
    ),
    (
        "Contextual",
        "contextual",
        "Contextual content built around a relevant target page.",
        800,
        "Make the topic useful on its own and integrate the target URL naturally without keyword stuffing.",
    ),
    (
        "LLM Blog (Short Blog)",
        "llm-blog-short-blog",
        "Concise blog content optimized for clear AI-readable answers.",
        500,
        "Answer the main intent early, use short sections, and keep statements direct and well structured.",
    ),
    (
        "Others",
        "others",
        "Flexible content for formats outside the standard starter types.",
        1000,
        "Follow the task notes and project instructions for the requested format.",
    ),
)

DEFAULT_PROMPT = """Write a comprehensive {{ content_type }} about {{ title }}.
Primary keyword: {{ primary_keyword }}
Target length: {{ word_count }} words.
Follow the supplied project context and return valid JSON with keys: title, meta_description, slug, and body."""


def add_starter_content_types(apps, schema_editor):
    user_model = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    content_type_model = apps.get_model("content_types", "ContentType")
    prompt_model = apps.get_model("prompts", "PromptTemplate")

    for owner in user_model.objects.all().iterator():
        for name, slug, description, word_count, requirements in STARTER_CONTENT_TYPES:
            content_type, _ = content_type_model.objects.get_or_create(
                owner_id=owner.pk,
                slug=slug,
                defaults={
                    "name": name,
                    "description": description,
                    "default_word_count": word_count,
                    "requirements": requirements,
                    "is_active": True,
                },
            )
            prompt_model.objects.get_or_create(
                owner_id=owner.pk,
                content_type_id=content_type.pk,
                project_id=None,
                defaults={"template": DEFAULT_PROMPT, "is_active": True},
            )


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("content_types", "0001_initial"),
        ("prompts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(add_starter_content_types, migrations.RunPython.noop),
    ]
