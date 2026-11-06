from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from clients.models import Customer, Property
from jobs.models import Job
from leads.models import Lead
from quoting.models import Quote, QuoteLine, RateCardItem
from quoting.services import (
    accept_quote,
    build_quote_from_lead,
    ensure_default_rate_card,
    lose_quote,
    send_quote,
)

User = get_user_model()


class QuoteLifecycleTests(TestCase):
    def setUp(self):
        self.card = ensure_default_rate_card()
        self.exterior = self.card.items.get(code="exterior")
        self.screens = self.card.items.get(code="screens")
        self.lead = Lead.objects.create(
            name="Pat Homeowner",
            email="pat@example.com",
            phone="555-010-7777",
            address_line1="200 Lake St",
            city="Cedar Falls",
            zip_code="50613",
            service_interest=Lead.ServiceInterest.EXTERIOR,
            window_pane_estimate=10,
        )

    def test_build_itemized_quote_from_rate_card(self):
        quote = build_quote_from_lead(
            self.lead,
            [
                {"item": self.exterior, "quantity": Decimal("10")},
                {"item": self.screens, "quantity": Decimal("4")},
            ],
        )
        self.assertEqual(quote.status, Quote.Status.DRAFT)
        self.assertEqual(quote.lines.count(), 2)
        self.assertEqual(quote.customer_email, "pat@example.com")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Status.QUOTED)
        # 10*6 + 4*3.50 = 60 + 14 = 74; min 125 → total 125
        self.assertEqual(quote.subtotal, Decimal("74.00"))
        self.assertEqual(quote.minimum_charge, Decimal("125.00"))
        self.assertEqual(quote.total, Decimal("125.00"))

    def test_totals_honor_minimum_charge(self):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("2")}],
        )
        self.assertEqual(quote.subtotal, Decimal("12.00"))
        self.assertEqual(quote.total, quote.minimum_charge)
        self.assertGreater(quote.total, quote.subtotal)

    def test_totals_above_minimum_use_subtotal(self):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("30")}],
        )
        self.assertEqual(quote.subtotal, Decimal("180.00"))
        self.assertEqual(quote.total, Decimal("180.00"))

    @override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
    def test_sending_emails_the_customer(self):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("10")}],
        )
        self.client.force_login(
            User.objects.create_user(username="jordan", password="test-pass-12345")
        )
        response = self.client.post(reverse("quoting:send", kwargs={"pk": quote.pk}))
        self.assertRedirects(response, reverse("quoting:detail", kwargs={"pk": quote.pk}))
        quote.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.SENT)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["pat@example.com"])
        self.assertIn("Total: $", mail.outbox[0].body)

    def test_accept_creates_customer_property_and_marks_lead_won(self):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("10")}],
        )
        accept_quote(quote)
        quote.refresh_from_db()
        self.lead.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.ACCEPTED)
        self.assertIsNotNone(quote.customer_id)
        self.assertIsNotNone(quote.property_id)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Property.objects.count(), 1)
        customer = quote.customer
        prop = quote.property
        self.assertEqual(customer.name, "Pat Homeowner")
        self.assertEqual(customer.email, "pat@example.com")
        self.assertEqual(prop.address_line1, "200 Lake St")
        self.assertEqual(prop.customer_id, customer.pk)
        self.assertEqual(self.lead.status, Lead.Status.WON)
        self.assertTrue(Job.objects.filter(quote=quote).exists())
        job = Job.objects.get(quote=quote)
        self.assertEqual(job.customer_id, quote.customer_id)
        self.assertEqual(job.property_id, quote.property_id)

    def test_lose_stores_a_reason(self):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("10")}],
        )
        lose_quote(quote, "Chose another cleaner")
        quote.refresh_from_db()
        self.lead.refresh_from_db()
        self.assertEqual(quote.status, Quote.Status.LOST)
        self.assertEqual(quote.lost_reason, "Chose another cleaner")
        self.assertEqual(self.lead.status, Lead.Status.LOST)
        self.assertEqual(self.lead.lost_reason, "Chose another cleaner")

    def test_lose_requires_reason(self):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal("10")}],
        )
        with self.assertRaises(ValueError):
            lose_quote(quote, "  ")


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class QuoteOwnerUITests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jordan", password="test-pass-12345")
        self.client.login(username="jordan", password="test-pass-12345")
        self.card = ensure_default_rate_card()
        self.lead = Lead.objects.create(
            name="UI Lead",
            email="ui@example.com",
            phone="555-010-8888",
            address_line1="9 Oak Ave",
            city="Waterloo",
            zip_code="50701",
        )

    def test_build_quote_form_creates_quote(self):
        item = self.card.items.get(code="both")
        response = self.client.post(
            reverse("quoting:build_from_lead", kwargs={"lead_id": self.lead.pk}),
            {f"qty_{item.pk}": "8", "notes": "Spring clean"},
        )
        quote = Quote.objects.get()
        self.assertRedirects(response, reverse("quoting:detail", kwargs={"pk": quote.pk}))
        self.assertEqual(quote.lines.count(), 1)
        self.assertEqual(quote.notes, "Spring clean")

    def test_rate_card_minimum_editable(self):
        response = self.client.post(
            reverse("quoting:rate_card"),
            {"form": "settings", "minimum_charge": "150.00"},
        )
        self.assertRedirects(response, reverse("quoting:rate_card"))
        self.card.refresh_from_db()
        self.assertEqual(self.card.minimum_charge, Decimal("150.00"))

    def test_customer_list_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse("clients:list"))
        self.assertEqual(response.status_code, 302)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class QuoteTransitionGuardTests(TestCase):
    def setUp(self):
        card = ensure_default_rate_card()
        self.lead = Lead.objects.create(
            name="Guard Lead", email="guard@example.com", phone="555-010-8888",
            address_line1="3 Lake St",
        )
        self.quote = build_quote_from_lead(
            self.lead, [{"item": card.items.get(code="exterior"), "quantity": Decimal("10")}]
        )

    def test_resend_refreshes_sent_at(self):
        send_quote(self.quote)
        first = Quote.objects.get(pk=self.quote.pk).sent_at
        send_quote(self.quote)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.SENT)
        self.assertGreater(self.quote.sent_at, first)
        self.assertEqual(len(mail.outbox), 2)

    def test_accept_twice_creates_one_customer_property_job(self):
        accept_quote(self.quote)
        accept_quote(Quote.objects.get(pk=self.quote.pk))
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Property.objects.count(), 1)
        self.assertEqual(Job.objects.filter(quote=self.quote).count(), 1)

    def test_send_or_lose_accepted_quote_refused(self):
        accept_quote(self.quote)
        mail.outbox.clear()
        with self.assertRaises(ValueError):
            send_quote(self.quote)
        with self.assertRaises(ValueError):
            lose_quote(self.quote, "changed mind")
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.ACCEPTED)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 0)

    def test_lost_quote_cannot_be_accepted_or_sent(self):
        lose_quote(self.quote, "too pricey")
        with self.assertRaises(ValueError):
            accept_quote(self.quote)
        with self.assertRaises(ValueError):
            send_quote(self.quote)
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.LOST)
        self.assertEqual(Customer.objects.count(), 0)

    def test_view_posts_on_accepted_quote(self):
        User.objects.create_user(username="owner", password="test-pass-12345")
        self.client.login(username="owner", password="test-pass-12345")
        accept_quote(self.quote)
        self.client.post(reverse("quoting:send", kwargs={"pk": self.quote.pk}))
        self.client.post(reverse("quoting:lose", kwargs={"pk": self.quote.pk}), {"lost_reason": "x"})
        self.client.post(reverse("quoting:accept", kwargs={"pk": self.quote.pk}))
        self.quote.refresh_from_db()
        self.assertEqual(self.quote.status, Quote.Status.ACCEPTED)
        self.assertEqual(Customer.objects.count(), 1)
        self.assertEqual(Job.objects.filter(quote=self.quote).count(), 1)
