from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from followup.models import RecurringPlan, ReviewRequest
from followup.services import send_review_request_for_job, upsert_recurring_plan
from jobs.models import Job
from jobs.services import complete_job
from leads.models import Lead
from marketing.demo import GOOGLE_REVIEW_URL
from quoting.services import accept_quote, build_quote_from_lead, ensure_default_rate_card

User = get_user_model()


def _completed_job_with_email():
    card = ensure_default_rate_card()
    lead = Lead.objects.create(
        name="Review Customer",
        email="review@example.com",
        phone="555-010-8000",
        address_line1="12 Thanks Ave",
        city="Cedar Falls",
        zip_code="50613",
    )
    quote = build_quote_from_lead(
        lead,
        [{"item": card.items.get(code="exterior"), "quantity": Decimal("10")}],
    )
    accept_quote(quote)
    job = Job.objects.get(quote=quote)
    complete_job(job)
    return job


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ReviewRequestTests(TestCase):
    def test_sending_review_request_creates_record_and_emails_url(self):
        job = _completed_job_with_email()
        rr = send_review_request_for_job(job)
        self.assertEqual(ReviewRequest.objects.count(), 1)
        self.assertEqual(rr.job_id, job.pk)
        self.assertEqual(rr.customer_id, job.customer_id)
        self.assertEqual(rr.google_review_url, GOOGLE_REVIEW_URL)
        self.assertEqual(rr.recipient_email, "review@example.com")
        self.assertIsNotNone(rr.sent_at)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(GOOGLE_REVIEW_URL, mail.outbox[0].body)
        self.assertEqual(mail.outbox[0].to, ["review@example.com"])


class RecurringPlanTests(TestCase):
    def test_recurring_plan_stores_frequency_next_date_discount(self):
        job = _completed_job_with_email()
        next_date = date.today() + timedelta(days=180)
        plan = upsert_recurring_plan(
            customer=job.customer,
            property=job.property,
            frequency=RecurringPlan.Frequency.BIANNUAL,
            next_service_date=next_date,
            discount_percent=Decimal("15.00"),
            notes="Spring/fall offer",
        )
        plan.refresh_from_db()
        self.assertEqual(plan.frequency, RecurringPlan.Frequency.BIANNUAL)
        self.assertEqual(plan.next_service_date, next_date)
        self.assertEqual(plan.discount_percent, Decimal("15.00"))
        self.assertTrue(plan.is_active)

        updated = upsert_recurring_plan(
            customer=job.customer,
            property=job.property,
            frequency=RecurringPlan.Frequency.QUARTERLY,
            next_service_date=next_date + timedelta(days=30),
            discount_percent=Decimal("10.00"),
            plan=plan,
        )
        self.assertEqual(updated.pk, plan.pk)
        self.assertEqual(updated.frequency, RecurringPlan.Frequency.QUARTERLY)
        self.assertEqual(updated.discount_percent, Decimal("10.00"))


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class FollowupOwnerAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jordan", password="test-pass-12345")
        self.job = _completed_job_with_email()

    def test_unauthenticated_cannot_send_or_view_followup(self):
        urls_get = [
            reverse("followup:home"),
            reverse(
                "followup:plan_create",
                kwargs={
                    "customer_id": self.job.customer_id,
                    "property_id": self.job.property_id,
                },
            ),
        ]
        for url in urls_get:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response["Location"])

        response = self.client.post(
            reverse("followup:send_review_ask", kwargs={"job_id": self.job.pk})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse("accounts:login"), response["Location"])
        self.assertEqual(ReviewRequest.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_owner_can_send_review_ask_from_job(self):
        self.client.login(username="jordan", password="test-pass-12345")
        response = self.client.post(
            reverse("followup:send_review_ask", kwargs={"job_id": self.job.pk})
        )
        self.assertRedirects(response, reverse("jobs:detail", kwargs={"pk": self.job.pk}))
        self.assertEqual(ReviewRequest.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)
