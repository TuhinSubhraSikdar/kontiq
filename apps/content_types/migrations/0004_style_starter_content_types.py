from django.db import migrations


STARTER_STYLES = {
    "web-20": ("seo", "globe", "#126BFF"),
    "blog-posting": ("editorial", "file-text", "#7C3AED"),
    "pr-submission": ("pr", "newspaper", "#0891B2"),
    "contextual": ("seo", "bookmark", "#2563EB"),
    "llm-blog-short-blog": ("editorial", "sparkles", "#DB2777"),
    "others": ("custom", "layout", "#64748B"),
}


def style_starters(apps, schema_editor):
    ContentType = apps.get_model("content_types", "ContentType")
    for slug, (category, icon, color) in STARTER_STYLES.items():
        ContentType.objects.filter(
            slug=slug,
            category="custom",
            icon="file-text",
            color="#126BFF",
        ).update(category=category, icon=icon, color=color)


def unstyle_starters(apps, schema_editor):
    ContentType = apps.get_model("content_types", "ContentType")
    ContentType.objects.filter(slug__in=STARTER_STYLES).update(
        category="custom", icon="file-text", color="#126BFF"
    )


class Migration(migrations.Migration):
    dependencies = [("content_types", "0003_contenttype_category_contenttype_color_and_more")]

    operations = [migrations.RunPython(style_starters, unstyle_starters)]
