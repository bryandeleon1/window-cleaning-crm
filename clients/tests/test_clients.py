from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from clients.models import Customer, Property

User = get_user_model()


class OwnerEditTests(TestCase):
    def setUp(self):
        User.objects.create_user(username="owner", password="test-pass-12345")
        self.customer = Customer.objects.create(name="Sam", phone="555-010-1212")
        self.prop = Property.objects.create(customer=self.customer, address_line1="1 Old St")
        self.other = Customer.objects.create(name="Other")
        self.edit_url = reverse("clients:edit", kwargs={"pk": self.customer.pk})
        self.prop_url = reverse(
            "clients:property_edit",
            kwargs={"pk": self.customer.pk, "property_pk": self.prop.pk},
        )

    def test_unauthenticated_redirected(self):
        for url in (self.edit_url, self.prop_url):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertIn(reverse("accounts:login"), response["Location"])

    def test_owner_updates_contact_fields(self):
        self.client.login(username="owner", password="test-pass-12345")
        response = self.client.post(
            self.edit_url,
            {"name": "Sam Lee", "email": "sam@example.com", "phone": "555-010-3434", "notes": "Gate"},
        )
        self.assertRedirects(response, reverse("clients:detail", kwargs={"pk": self.customer.pk}))
        self.customer.refresh_from_db()
        self.assertEqual(
            (self.customer.name, self.customer.email, self.customer.phone, self.customer.notes),
            ("Sam Lee", "sam@example.com", "555-010-3434", "Gate"),
        )

    def test_owner_updates_property_fields(self):
        self.client.login(username="owner", password="test-pass-12345")
        response = self.client.post(
            self.prop_url,
            {
                "label": "Home",
                "address_line1": "2 New St",
                "city": "Waterloo",
                "state": "IA",
                "zip_code": "50701",
                "access_pets": "Dog",
                "access_alarms": "None",
                "access_parking": "Driveway",
                "access_notes": "Side gate",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.prop.refresh_from_db()
        self.assertEqual(self.prop.address_line1, "2 New St")
        self.assertEqual(self.prop.access_pets, "Dog")
        self.assertEqual(self.prop.access_parking, "Driveway")

    def test_property_of_other_customer_is_404(self):
        self.client.login(username="owner", password="test-pass-12345")
        url = reverse(
            "clients:property_edit",
            kwargs={"pk": self.other.pk, "property_pk": self.prop.pk},
        )
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_detail_links_edit_screens(self):
        self.client.login(username="owner", password="test-pass-12345")
        response = self.client.get(reverse("clients:detail", kwargs={"pk": self.customer.pk}))
        self.assertContains(response, self.edit_url)
        self.assertContains(response, self.prop_url)
