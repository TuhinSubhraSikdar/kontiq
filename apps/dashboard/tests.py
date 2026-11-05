from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .services import get_dashboard_snapshot


class DashboardViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = get_user_model().objects.create_user(
            username="dashboard-user",
            first_name="Avery",
            password="strong-dashboard-password-9021",
        )

    def test_dashboard_requires_authentication(self):
        response = self.client.get(reverse("dashboard:index"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('dashboard:index')}",
        )

    def test_dashboard_renders_live_readiness_and_required_navigation(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back, Avery")
        self.assertContains(response, "Connected")
        for label in (
            "Dashboard",
            "Projects",
            "Content Tasks",
            "Prompt Manager",
            "AI Models",
            "Scheduler",
            "Content Library",
            "Activity Logs",
            "Settings",
        ):
            self.assertContains(response, label)

    def test_implemented_navigation_links_are_enabled(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse("dashboard:index"))

        self.assertNotContains(response, 'aria-disabled="true"')
        self.assertContains(response, reverse("projects:list"))
        self.assertContains(response, reverse("tasks:list"))
        self.assertContains(response, reverse("library:list"))

    def test_favicon_has_a_local_static_target(self):
        response = self.client.get(reverse("favicon"))

        self.assertRedirects(
            response,
            "/static/images/favicon.svg",
            status_code=301,
            fetch_redirect_response=False,
        )


class DashboardServiceTests(TestCase):
    def test_snapshot_uses_live_configuration_and_app_registry(self):
        snapshot = get_dashboard_snapshot()

        self.assertEqual(snapshot.health_checks[0].value, "Connected")
        self.assertEqual(snapshot.health_checks[1].value, "Ready")
        self.assertEqual(snapshot.health_checks[2].value, "Configured")
        self.assertTrue(snapshot.modules[0].is_available)
        self.assertTrue(all(module.is_available for module in snapshot.modules))
