from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class ReviewRequest(models.Model):
    """Review-ask sent for a completed job. Google URL is snapshotted at send time."""

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    sent_at = models.DateTimeField()

    job = models.ForeignKey(
        "jobs.Job",
        related_name="review_requests",
        on_delete=models.CASCADE,
    )
    customer = models.ForeignKey(
        "clients.Customer",
        related_name="review_requests",
        on_delete=models.CASCADE,
    )
    google_review_url = models.URLField(
        help_text="URL that was included in the email (copied from demo copy at send time).",
    )
    recipient_email = models.EmailField()

    class Meta:
        ordering = ["-sent_at", "-id"]

    def __str__(self) -> str:
        return f"Review ask for job {self.job_id} at {self.sent_at}"


class RecurringPlan(models.Model):
    """Recorded recurring offer — not membership billing or auto-charge."""

    class Frequency(models.TextChoices):
        BIANNUAL = "biannual", "Biannual (spring/fall)"
        QUARTERLY = "quarterly", "Quarterly"
        ANNUAL = "annual", "Annual"

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    customer = models.ForeignKey(
        "clients.Customer",
        related_name="recurring_plans",
        on_delete=models.CASCADE,
    )
    property = models.ForeignKey(
        "clients.Property",
        related_name="recurring_plans",
        on_delete=models.CASCADE,
    )
    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.BIANNUAL,
    )
    next_service_date = models.DateField()
    discount_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Optional percent off one-time rate (e.g. 10–20). Not an auto-charge.",
    )
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["next_service_date", "-id"]

    def __str__(self) -> str:
        return f"{self.customer} — {self.get_frequency_display()} next {self.next_service_date}"
