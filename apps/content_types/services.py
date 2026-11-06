from django.db import transaction

from apps.prompts.models import DEFAULT_PROMPT, PromptTemplate

from .models import ContentType


STARTER_CONTENT_TYPES = (
    {
        "name": "Web 2.0",
        "slug": "web-20",
        "description": "Supporting content for Web 2.0 publishing platforms.",
        "category": "seo",
        "icon": "globe",
        "color": "#126BFF",
        "default_word_count": 700,
        "requirements": "Write useful, self-contained content with a natural contextual reference to the target URL.",
    },
    {
        "name": "Blog Posting",
        "slug": "blog-posting",
        "description": "Long-form website or guest blog content.",
        "category": "editorial",
        "icon": "file-text",
        "color": "#7C3AED",
        "default_word_count": 1200,
        "requirements": "Use a clear introduction, descriptive headings, practical detail, and a concise conclusion.",
    },
    {
        "name": "PR Submission",
        "slug": "pr-submission",
        "description": "Press-release style announcements for submission platforms.",
        "category": "pr",
        "icon": "newspaper",
        "color": "#0891B2",
        "default_word_count": 600,
        "requirements": "Use a factual news angle, headline, opening summary, supporting details, and a company boilerplate.",
    },
    {
        "name": "Contextual",
        "slug": "contextual",
        "description": "Contextual content built around a relevant target page.",
        "category": "seo",
        "icon": "bookmark",
        "color": "#2563EB",
        "default_word_count": 800,
        "requirements": "Make the topic useful on its own and integrate the target URL naturally without keyword stuffing.",
    },
    {
        "name": "LLM Blog (Short Blog)",
        "slug": "llm-blog-short-blog",
        "description": "Concise blog content optimized for clear AI-readable answers.",
        "category": "editorial",
        "icon": "sparkles",
        "color": "#DB2777",
        "default_word_count": 500,
        "requirements": "Answer the main intent early, use short sections, and keep statements direct and well structured.",
    },
    {
        "name": "Others",
        "slug": "others",
        "description": "Flexible content for formats outside the standard starter types.",
        "category": "custom",
        "icon": "layout",
        "color": "#64748B",
        "default_word_count": 1000,
        "requirements": "Follow the task notes and project instructions for the requested format.",
    },
)


@transaction.atomic
def ensure_starter_content_types(owner):
    content_types = []
    for definition in STARTER_CONTENT_TYPES:
        content_type, _ = ContentType.objects.get_or_create(
            owner=owner,
            slug=definition["slug"],
            defaults={
                "name": definition["name"],
                "description": definition["description"],
                "category": definition["category"],
                "icon": definition["icon"],
                "color": definition["color"],
                "default_word_count": definition["default_word_count"],
                "requirements": definition["requirements"],
                "is_active": True,
            },
        )
        PromptTemplate.objects.get_or_create(
            owner=owner,
            content_type=content_type,
            project=None,
            defaults={"template": DEFAULT_PROMPT},
        )
        content_types.append(content_type)
    return content_types
