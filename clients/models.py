"""Customers and their service property. The app keeps one property per customer.
"""

from django.db import models
from django.utils import timezone


class Customer(models.Model):
    """Residential customer. One Property in MVP; more later is out of scope for this PR."""

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    # Nullable future-proof fields only — no commercial module in MVP.
    customer_type = models.CharField(max_length=40, blank=True)
    requires_coi = models.BooleanField(null=True, blank=True)
    billing_terms = models.CharField(max_length=80, blank=True)

    class Meta:
        ordering = ["name", "-created_at"]

    def __str__(self) -> str:
        return self.name


class Property(models.Model):
    """Service address for a customer. MVP creates one per accepted quote."""

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    customer = models.ForeignKey(
        Customer,
        related_name="properties",
        on_delete=models.CASCADE,
    )
    label = models.CharField(max_length=80, blank=True, default="Service address")
    address_line1 = models.CharField(max_length=200)
    city = models.CharField(max_length=100, blank=True)
    state = models.CharField(max_length=2, blank=True, default="IA")
    zip_code = models.CharField(max_length=10, blank=True)

    access_pets = models.CharField(max_length=255, blank=True)
    access_alarms = models.CharField(max_length=255, blank=True)
    access_parking = models.CharField(max_length=255, blank=True)
    access_notes = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "properties"
        ordering = ["customer__name", "id"]

    def __str__(self) -> str:
        return f"{self.customer.name} — {self.address_line1}"
