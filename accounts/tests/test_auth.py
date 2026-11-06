from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


User = get_user_model()


class OwnerAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="jordan",
            password="test-pass-12345",
        )

    def test_login_page_renders(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Sign in")

    def test_owner_can_log_in_and_reach_home(self):
        response = self.client.post(
            reverse("accounts:login"),
            {"username": "jordan", "password": "test-pass-12345"},
        )
        self.assertRedirects(response, reverse("accounts:home"))
        home = self.client.get(reverse("accounts:home"))
        self.assertEqual(home.status_code, 200)
        self.assertContains(home, "jordan")

    def test_home_requires_login(self):
        response = self.client.get(reverse("accounts:home"))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])

    def test_owner_can_log_out(self):
        self.client.login(username="jordan", password="test-pass-12345")
        response = self.client.post(reverse("accounts:logout"))
        self.assertRedirects(response, reverse("accounts:login"))
        home = self.client.get(reverse("accounts:home"))
        self.assertEqual(home.status_code, 302)
