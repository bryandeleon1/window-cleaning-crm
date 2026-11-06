from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from billing.models import Invoice, Payment
from billing.services import generate_invoice_for_job, record_payment, save_hosted_payment_url
from jobs.models import Job
from leads.models import Lead
from quoting.services import accept_quote, build_quote_from_lead, ensure_default_rate_card

User = get_user_model()


class InvoicePaymentTests(TestCase):
    def setUp(self):
        self.card = ensure_default_rate_card()
        self.exterior = self.card.items.get(code="exterior")
        self.lead = Lead.objects.create(
            name="Billable Customer",
            email="bill@example.com",
            phone="555-010-7000",
            address_line1="77 Ledger Ln",
            city="Cedar Falls",
            zip_code="50613",
        )

    def _accepted_job(self, window_qty: str = "5"):
        quote = build_quote_from_lead(
            self.lead,
            [{"item": self.exterior, "quantity": Decimal(window_qty)}],
        )
        accept_quote(quote)
        return Job.objects.get(quote=quote), quote

    def test_invoice_copies_quote_lines_and_minimum_total(self):
        job, quote = self._accepted_job("5")  # 5*6=30 < min 125
        self.assertEqual(quote.subtotal, Decimal("30.00"))
        self.assertEqual(quote.total, Decimal("125.00"))

        invoice = generate_invoice_for_job(job)
        self.assertEqual(invoice.lines.count(), quote.lines.count())
        self.assertEqual(invoice.minimum_charge, quote.minimum_charge)
        self.assertEqual(invoice.subtotal, quote.subtotal)
        self.assertEqual(invoice.total, quote.total)
        self.assertEqual(invoice.customer_id, job.customer_id)
        self.assertEqual(invoice.property_id, job.property_id)

        qline = quote.lines.get()
        iline = invoice.lines.get()
        self.assertEqual(iline.description, qline.description)
        self.assertEqual(iline.unit, qline.unit)
        self.assertEqual(iline.quantity, qline.quantity)
        self.assertEqual(iline.unit_price, qline.unit_price)
        self.assertEqual(iline.line_total, qline.line_total)
        self.assertEqual(iline.sort_order, qline.sort_order)

        # Idempotent
        again = generate_invoice_for_job(job)
        self.assertEqual(again.pk, invoice.pk)
        self.assertEqual(Invoice.objects.filter(job=job).count(), 1)

    def test_invoice_copies_above_minimum_total(self):
        job, quote = self._accepted_job("30")  # 180 > 125
        invoice = generate_invoice_for_job(job)
        self.assertEqual(invoice.subtotal, Decimal("180.00"))
        self.assertEqual(invoice.total, Decimal("180.00"))

    def test_record_cash_check_venmo_other(self):
        job, quote = self._accepted_job("30")
        invoice = generate_invoice_for_job(job)
        methods = [
            (Payment.Method.CASH, Decimal("40.00")),
            (Payment.Method.CHECK, Decimal("40.00")),
            (Payment.Method.VENMO, Decimal("50.00")),
            (Payment.Method.OTHER, Decimal("50.00")),
        ]
        for method, amount in methods:
            record_payment(invoice, amount=amount, method=method, note=method)
        invoice.refresh_from_db()
        self.assertEqual(invoice.payments.count(), 4)
        self.assertEqual(invoice.amount_paid, Decimal("180.00"))
        self.assertEqual(invoice.status, Invoice.Status.PAID)
        self.assertIsNotNone(invoice.paid_at)

    def test_hosted_payment_url_stores_without_charging(self):
        job, _quote = self._accepted_job("10")
        invoice = generate_invoice_for_job(job)
        url = "https://buy.stripe.com/test_placeholder_not_live"
        save_hosted_payment_url(invoice, url)
        invoice.refresh_from_db()
        self.assertEqual(invoice.hosted_payment_url, url)
        self.assertEqual(invoice.payments.count(), 0)
        self.assertEqual(invoice.status, Invoice.Status.OPEN)
        self.assertIsNone(invoice.paid_at)


class InvoiceOwnerAccessTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="jordan", password="test-pass-12345")
        card = ensure_default_rate_card()
        lead = Lead.objects.create(
            name="Access Customer",
            email="access@example.com",
            phone="555-010-7001",
            address_line1="1 Access Ave",
            city="Waterloo",
            zip_code="50701",
        )
        quote = build_quote_from_lead(
            lead,
            [{"item": card.items.get(code="exterior"), "quantity": Decimal("8")}],
        )
        accept_quote(quote)
        self.job = Job.objects.get(quote=quote)
        self.invoice = generate_invoice_for_job(self.job)

    def test_unauthenticated_cannot_reach_owner_invoice_views(self):
        urls = [
            reverse("billing:list"),
            reverse("billing:detail", kwargs={"pk": self.invoice.pk}),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response["Location"])

        post_urls = [
            reverse("billing:generate_from_job", kwargs={"job_id": self.job.pk}),
            reverse("billing:payment_create", kwargs={"pk": self.invoice.pk}),
            reverse("billing:hosted_url_save", kwargs={"pk": self.invoice.pk}),
        ]
        for url in post_urls:
            with self.subTest(url=url):
                response = self.client.post(url, {})
                self.assertEqual(response.status_code, 302)
                self.assertIn(reverse("accounts:login"), response["Location"])

    def test_owner_can_view_invoice_list_and_detail(self):
        self.client.login(username="jordan", password="test-pass-12345")
        list_resp = self.client.get(reverse("billing:list"))
        self.assertEqual(list_resp.status_code, 200)
        self.assertContains(list_resp, f"Invoice #{self.invoice.pk}")
        detail = self.client.get(reverse("billing:detail", kwargs={"pk": self.invoice.pk}))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "Stripe Payment Link")
