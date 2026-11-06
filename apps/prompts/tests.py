from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from apps.content_types.models import ContentType
from apps.projects.models import Project

from .forms import PromptTemplateForm
from .models import PromptTemplate, PromptVersion
from .services import render_prompt


class PromptTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="writer")
        self.content_type = ContentType.objects.create(owner=self.user, name="Article")
        self.project = Project.objects.create(owner=self.user, name="Acme")

    def test_restricted_renderer_only_substitutes_documented_variables(self):
        self.assertEqual(render_prompt("Write {{ title }} for {{ project_name }}", {"title": "SEO", "project_name": "Acme"}), "Write SEO for Acme")

    def test_unknown_template_variable_is_rejected(self):
        form = PromptTemplateForm(
            data={"content_type": self.content_type.pk, "project": "", "template": "Hello {{ secret_key }}", "is_active": True},
            owner=self.user,
        )
        self.assertFalse(form.is_valid())
        self.assertIn("Unsupported variables", form.errors["template"][0])

    def test_cross_owner_choices_are_rejected(self):
        other = get_user_model().objects.create_user(username="other-writer")
        other_type = ContentType.objects.create(owner=other, name="Other")
        form = PromptTemplateForm(
            data={"content_type": other_type.pk, "project": "", "template": "Write {{ title }}", "is_active": True},
            owner=self.user,
        )
        self.assertFalse(form.is_valid())

    def test_workspace_library_favorite_and_version_restore(self):
        prompt = PromptTemplate.objects.create(
            owner=self.user,
            content_type=self.content_type,
            title="Authority article",
            template="Write {{ title }}",
        )
        self.client.force_login(self.user)

        workspace = self.client.get(
            reverse("prompts:content_type_workspace", args=[self.content_type.pk])
        )
        library = self.client.get(reverse("prompts:library"), {"q": "Authority"})
        self.assertContains(workspace, "Authority article")
        self.assertContains(library, "Authority article")

        self.client.post(reverse("prompts:favorite", args=[prompt.pk]))
        prompt.refresh_from_db()
        self.assertTrue(prompt.is_favorite)

        response = self.client.post(
            reverse("prompts:edit", args=[prompt.pk]),
            {
                "title": "Authority article",
                "description": "Updated workflow",
                "content_type": self.content_type.pk,
                "project": "",
                "category": PromptTemplate.Category.WRITING,
                "template": "Draft {{ title }} for {{ audience }}",
                "is_active": "on",
            },
        )
        self.assertRedirects(response, reverse("prompts:edit", args=[prompt.pk]))
        prompt.refresh_from_db()
        self.assertEqual(prompt.version, 2)
        version = PromptVersion.objects.get(prompt=prompt, version=1)
        self.assertEqual(version.template, "Write {{ title }}")

        self.client.post(
            reverse("prompts:version_restore", args=[prompt.pk, version.pk])
        )
        prompt.refresh_from_db()
        self.assertEqual(prompt.template, "Write {{ title }}")
        self.assertEqual(prompt.version, 3)

    def test_content_type_duplicate_copies_its_prompt_workspace(self):
        source_prompt = PromptTemplate.objects.create(
            owner=self.user,
            content_type=self.content_type,
            title="Source prompt",
            template="Write {{ title }} for {{ project_name }}",
        )
        self.client.force_login(self.user)
        response = self.client.post(
            f"{reverse('prompts:content_type_create')}?duplicate={self.content_type.pk}",
            {
                "name": "Article copy",
                "description": "Duplicated format",
                "category": ContentType.Category.EDITORIAL,
                "icon": "file-text",
                "color": "#126BFF",
                "default_word_count": 1200,
                "requirements": "Use clear headings.",
                "custom_fields_input": "Author bio",
                "is_active": "on",
            },
        )
        duplicated = ContentType.objects.get(owner=self.user, name="Article copy")
        self.assertRedirects(
            response,
            reverse("prompts:content_type_workspace", args=[duplicated.pk]),
        )
        copied_prompt = duplicated.prompt_templates.get()
        self.assertEqual(copied_prompt.template, source_prompt.template)
        self.assertEqual(duplicated.custom_fields, ["Author bio"])
