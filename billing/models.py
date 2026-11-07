"""Invoices and recorded payments. Payment is invoice-only; any Stripe link is a
placeholder URL and nothing is charged by this app.
"""

from decimal import Decimal
import builtins

from django.db import models
from django.db.models import Sum
from django.utils import timezone


class Invoice(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        OPEN = "open", "Open"
        PAID = "paid", "Paid"
        VOID = "void", "Void"

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    job = models.OneToOneField(
        "jobs.Job",
        related_name="invoice",
        on_delete=models.CASCADE,
    )
    customer = models.ForeignKey(
        "clients.Customer",
        related_name="invoices",
        on_delete=models.PROTECT,
    )
    property = models.ForeignKey(
        "clients.Property",
        related_name="invoices",
        on_delete=models.PROTECT,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    # Snapshots from the quote at generation time.
    minimum_charge = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    # Stripe Payment Link / hosted-invoice placeholder only — never charged by this app.
    hosted_payment_url = models.URLField(
        blank=True,
        help_text="Optional future Stripe Payment Link or hosted invoice URL. Placeholder only — saving does not charge.",
    )
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Invoice #{self.pk} ({self.get_status_display()})"

    @builtins.property
    def amount_paid(self) -> Decimal:
        agg = self.payments.aggregate(s=Sum("amount"))
        return agg["s"] or Decimal("0.00")

    @builtins.property
    def balance_due(self) -> Decimal:
        return self.total - self.amount_paid


class InvoiceLine(models.Model):
    invoice = models.ForeignKey(Invoice, related_name="lines", on_delete=models.CASCADE)
    description = models.CharField(max_length=200)
    unit = models.CharField(max_length=20, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("1"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]

    def __str__(self) -> str:
        return self.description


class Payment(models.Model):
    class Method(models.TextChoices):
        CASH = "cash", "Cash"
        CHECK = "check", "Check"
        VENMO = "venmo", "Venmo"
        OTHER = "other", "Other"

    invoice = models.ForeignKey(Invoice, related_name="payments", on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.CharField(max_length=20, choices=Method.choices)
    recorded_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    # Stripe / other processor stubs — no PAN, CVV, or card expiry fields.
    provider = models.CharField(max_length=40, blank=True)
    external_id = models.CharField(max_length=120, blank=True)

    class Meta:
        ordering = ["-recorded_at", "-id"]

    def __str__(self) -> str:
        return f"{self.get_method_display()} ${self.amount} on invoice {self.invoice_id}"
