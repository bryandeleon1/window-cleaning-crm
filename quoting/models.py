from decimal import Decimal

from django.db import models
from django.db.models import Sum
from django.utils import timezone


class RateCard(models.Model):
    """Editable rate card. Single-tenant demo uses one active card."""

    name = models.CharField(max_length=80, default="Standard")
    minimum_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("125.00"),
        help_text="Quote total will not go below this amount.",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name


class RateCardItem(models.Model):
    class Unit(models.TextChoices):
        PER_WINDOW = "per_window", "Per window"
        PER_PANE = "per_pane", "Per pane"
        EACH = "each", "Each"
        FLAT = "flat", "Flat"

    rate_card = models.ForeignKey(
        RateCard,
        related_name="items",
        on_delete=models.CASCADE,
    )
    code = models.SlugField(max_length=40)
    name = models.CharField(max_length=120)
    unit = models.CharField(max_length=20, choices=Unit.choices, default=Unit.PER_WINDOW)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    is_addon = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        unique_together = [("rate_card", "code")]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_unit_display()})"


class Quote(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SENT = "sent", "Sent"
        ACCEPTED = "accepted", "Accepted"
        LOST = "lost", "Lost"

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)

    lead = models.ForeignKey(
        "leads.Lead",
        related_name="quotes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    customer = models.ForeignKey(
        "clients.Customer",
        related_name="quotes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    property = models.ForeignKey(
        "clients.Property",
        related_name="quotes",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    lost_reason = models.CharField(max_length=255, blank=True)
    notes = models.TextField(blank=True)

    # Snapshots so later rate-card edits do not rewrite sent quotes.
    customer_name = models.CharField(max_length=120, blank=True)
    customer_email = models.EmailField(blank=True)
    customer_phone = models.CharField(max_length=40, blank=True)
    service_address = models.CharField(max_length=255, blank=True)

    minimum_charge = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
    )
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Quote #{self.pk} ({self.get_status_display()})"

    def recalculate_totals(self, save: bool = True) -> None:
        agg = self.lines.aggregate(s=Sum("line_total"))
        subtotal = agg["s"] or Decimal("0.00")
        self.subtotal = subtotal
        self.total = max(subtotal, self.minimum_charge or Decimal("0.00"))
        if save:
            self.save(update_fields=["subtotal", "total", "updated_at"])


class QuoteLine(models.Model):
    quote = models.ForeignKey(Quote, related_name="lines", on_delete=models.CASCADE)
    rate_card_item = models.ForeignKey(
        RateCardItem,
        related_name="quote_lines",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
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

    def recalculate_line_total(self) -> None:
        self.line_total = (self.quantity or Decimal("0")) * (self.unit_price or Decimal("0"))
