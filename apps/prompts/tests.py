from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.content_types.models import ContentType
from apps.projects.models import Project

from .forms import PromptTemplateForm
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
