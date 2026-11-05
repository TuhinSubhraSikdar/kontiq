from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.prompts.models import PromptTemplate

from .models import ContentType
from .services import STARTER_CONTENT_TYPES, ensure_starter_content_types


class StarterContentTypeTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="starter-types")

    def test_new_users_receive_all_starter_types_and_prompts(self):
        expected_names = {definition["name"] for definition in STARTER_CONTENT_TYPES}
        content_types = ContentType.objects.filter(owner=self.user, slug__in={
            definition["slug"] for definition in STARTER_CONTENT_TYPES
        })
        self.assertEqual(set(content_types.values_list("name", flat=True)), expected_names)
        self.assertEqual(
            PromptTemplate.objects.filter(
                owner=self.user,
                content_type__in=content_types,
                project__isnull=True,
            ).count(),
            len(STARTER_CONTENT_TYPES),
        )

    def test_provisioning_is_idempotent_and_preserves_user_edits(self):
        web_type = ContentType.objects.get(owner=self.user, slug="web-20")
        web_type.description = "My customized description"
        web_type.save(update_fields=["description"])

        ensure_starter_content_types(self.user)

        web_type.refresh_from_db()
        self.assertEqual(web_type.description, "My customized description")
        self.assertEqual(
            ContentType.objects.filter(
                owner=self.user,
                slug__in={definition["slug"] for definition in STARTER_CONTENT_TYPES},
            ).count(),
            len(STARTER_CONTENT_TYPES),
        )
