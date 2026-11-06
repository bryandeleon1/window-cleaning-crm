from django.contrib.auth import get_user_model
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings

from billing.models import Invoice, Payment
from clients.models import Customer, Property
from followup.models import RecurringPlan, ReviewRequest
from jobs.models import Job
from leads.models import Lead
from quoting.models import Quote, RateCard


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class SeedDemoTests(TestCase):
    def test_seed_demo_creates_full_loop(self):
        call_command("seed_demo", verbosity=0)

        User = get_user_model()
        owner = User.objects.get(username="jordan")
        self.assertTrue(owner.check_password("demo-pass-12345"))

        self.assertTrue(RateCard.objects.exists())
        self.assertGreaterEqual(Lead.objects.count(), 4)
        self.assertTrue(Lead.objects.filter(status=Lead.Status.NEW).exists())
        lost = Lead.objects.get(status=Lead.Status.LOST)
        self.assertTrue(lost.lost_reason)

        self.assertTrue(Quote.objects.filter(status=Quote.Status.ACCEPTED).exists())
        self.assertGreaterEqual(Customer.objects.count(), 1)
        self.assertGreaterEqual(Property.objects.count(), 1)
        self.assertTrue(Job.objects.filter(status=Job.Status.COMPLETED).exists())
        self.assertTrue(Job.objects.filter(status=Job.Status.WEATHER_HOLD).exists())

        completed = Job.objects.get(status=Job.Status.COMPLETED)
        invoice = Invoice.objects.get(job=completed)
        self.assertTrue(Payment.objects.filter(invoice=invoice).exists())
        self.assertEqual(invoice.status, Invoice.Status.PAID)

        self.assertTrue(ReviewRequest.objects.filter(job=completed).exists())
        plan = RecurringPlan.objects.get(customer=completed.customer)
        self.assertEqual(plan.frequency, RecurringPlan.Frequency.BIANNUAL)
        self.assertIsNotNone(plan.next_service_date)

        # Review ask email went to locmem
        self.assertTrue(any("review" in m.subject.lower() for m in mail.outbox))

        # All emails fictional
        for lead in Lead.objects.all():
            if lead.email:
                self.assertTrue(lead.email.endswith("@example.com"))

    def test_seed_demo_is_idempotent(self):
        call_command("seed_demo", verbosity=0)
        counts = {
            "leads": Lead.objects.count(),
            "quotes": Quote.objects.count(),
            "customers": Customer.objects.count(),
            "jobs": Job.objects.count(),
            "invoices": Invoice.objects.count(),
            "payments": Payment.objects.count(),
            "reviews": ReviewRequest.objects.count(),
            "plans": RecurringPlan.objects.count(),
        }
        call_command("seed_demo", verbosity=0)
        self.assertEqual(Lead.objects.count(), counts["leads"])
        self.assertEqual(Quote.objects.count(), counts["quotes"])
        self.assertEqual(Customer.objects.count(), counts["customers"])
        self.assertEqual(Job.objects.count(), counts["jobs"])
        self.assertEqual(Invoice.objects.count(), counts["invoices"])
        self.assertEqual(Payment.objects.count(), counts["payments"])
        self.assertEqual(ReviewRequest.objects.count(), counts["reviews"])
        self.assertEqual(RecurringPlan.objects.count(), counts["plans"])
