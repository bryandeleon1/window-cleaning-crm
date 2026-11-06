"""Invoice generation and payment recording (no Stripe SDK / charges)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from jobs.models import Job

from .models import Invoice, InvoiceLine, Payment


@transaction.atomic
def generate_invoice_for_job(job: Job) -> Invoice:
    """Create an invoice from the job's quote lines/totals. Idempotent."""
    existing = Invoice.objects.filter(job=job).first()
    if existing:
        return existing

    quote = job.quote
    invoice = Invoice.objects.create(
        job=job,
        customer=job.customer,
        property=job.property,
        status=Invoice.Status.OPEN,
        minimum_charge=quote.minimum_charge,
        subtotal=quote.subtotal,
        total=quote.total,
    )
    for line in quote.lines.all():
        InvoiceLine.objects.create(
            invoice=invoice,
            description=line.description,
            unit=line.unit,
            quantity=line.quantity,
            unit_price=line.unit_price,
            line_total=line.line_total,
            sort_order=line.sort_order,
        )
    return invoice


@transaction.atomic
def record_payment(
    invoice: Invoice,
    *,
    amount: Decimal,
    method: str,
    note: str = "",
    provider: str = "",
    external_id: str = "",
    recorded_at=None,
) -> Payment:
    if amount is None or Decimal(amount) <= 0:
        raise ValueError("Payment amount must be positive.")
    if method not in {c.value for c in Payment.Method}:
        raise ValueError(f"Unknown payment method: {method}")

    payment = Payment.objects.create(
        invoice=invoice,
        amount=Decimal(amount),
        method=method,
        note=note or "",
        provider=provider or "",
        external_id=external_id or "",
        recorded_at=recorded_at or timezone.now(),
    )
    _refresh_invoice_paid_status(invoice)
    return payment


def _refresh_invoice_paid_status(invoice: Invoice) -> None:
    invoice.refresh_from_db()
    if invoice.status == Invoice.Status.VOID:
        return
    if invoice.amount_paid >= invoice.total and invoice.total > 0:
        invoice.status = Invoice.Status.PAID
        invoice.paid_at = timezone.now()
        invoice.save(update_fields=["status", "paid_at", "updated_at"])
    elif invoice.status == Invoice.Status.PAID and invoice.amount_paid < invoice.total:
        invoice.status = Invoice.Status.OPEN
        invoice.paid_at = None
        invoice.save(update_fields=["status", "paid_at", "updated_at"])


def save_hosted_payment_url(invoice: Invoice, url: str) -> Invoice:
    """Store a Stripe Payment Link placeholder URL. Does not charge or record payment."""
    invoice.hosted_payment_url = (url or "").strip()
    invoice.save(update_fields=["hosted_payment_url", "updated_at"])
    return invoice
