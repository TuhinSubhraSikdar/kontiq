from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class AuthenticationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.credentials = {
            "username": "phase-zero-user",
            "password": "a-strong-local-test-password-9081",
        }
        cls.user = get_user_model().objects.create_user(**cls.credentials)

    def test_home_redirects_anonymous_users_to_login(self):
        response = self.client.get(reverse("core:home"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('core:home')}",
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in to Kontiq")
        self.assertContains(response, 'name="csrfmiddlewaretoken"')

    def test_valid_login_redirects_to_authenticated_home(self):
        response = self.client.post(reverse("login"), self.credentials)

        self.assertRedirects(response, reverse("dashboard:index"))
        home_response = self.client.get(reverse("dashboard:index"))
        self.assertEqual(home_response.status_code, 200)
        self.assertContains(home_response, self.user.username)

    def test_authenticated_user_can_log_out_with_post(self):
        self.client.force_login(self.user)

        response = self.client.post(reverse("logout"))

        self.assertRedirects(response, reverse("login"))
        self.assertNotIn("_auth_user_id", self.client.session)
