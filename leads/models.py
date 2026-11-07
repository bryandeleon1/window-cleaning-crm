"""Lead = a quote request from a prospective customer (web form, phone, or webhook).

Leads are requests, not bookings; the owner confirms work by accepting a quote.
Lead photos are private and served only to the logged-in owner.
"""

from django.db import models
from django.utils import timezone


class Lead(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        QUOTED = "quoted", "Quoted"
        WON = "won", "Won"
        LOST = "lost", "Lost"
        SPAM = "spam", "Spam"

    class Source(models.TextChoices):
        WEB_FORM = "web_form", "Web form"
        PHONE = "phone", "Phone"
        WEBHOOK = "webhook", "Webhook"
        OTHER = "other", "Other"

    class ServiceInterest(models.TextChoices):
        EXTERIOR = "exterior", "Exterior"
        INTERIOR = "interior", "Interior"
        BOTH = "both", "Interior + exterior"
        UNSURE = "unsure", "Not sure yet"

    class HeardAbout(models.TextChoices):
        GOOGLE = "google", "Google"
        REFERRAL = "referral", "Referral"
        NEXTDOOR = "nextdoor", "Nextdoor"
        INSTAGRAM = "instagram", "Instagram"
        ANGI_THUMBTACK = "angi_thumbtack", "Angi / Thumbtack"
        YARD_SIGN = "yard_sign", "Yard sign"
        OTHER = "other", "Other"

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        db_index=True,
    )
    lost_reason = models.CharField(max_length=255, blank=True)
    source = models.CharField(
        max_length=20,
        choices=Source.choices,
        default=Source.WEB_FORM,
    )

    name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)

    address_line1 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=100, blank=True)
    zip_code = models.CharField(max_length=10, blank=True)

    service_interest = models.CharField(
        max_length=20,
        choices=ServiceInterest.choices,
        default=ServiceInterest.UNSURE,
    )
    stories = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Approximate number of stories.",
    )
    window_pane_estimate = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Approximate window or pane count.",
        verbose_name="window/pane estimate",
    )
    how_heard = models.CharField(
        max_length=32,
        choices=HeardAbout.choices,
        blank=True,
        verbose_name="how they heard",
    )
    message = models.TextField(blank=True)
    owner_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.get_status_display()})"


def lead_photo_upload_to(instance: "LeadPhoto", filename: str) -> str:
    return f"leads/{instance.lead_id}/{filename}"


class LeadPhoto(models.Model):
    """Private upload attached to a lead — not shown on public marketing pages."""

    lead = models.ForeignKey(Lead, related_name="photos", on_delete=models.CASCADE)
    image = models.FileField(upload_to=lead_photo_upload_to)
    uploaded_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self) -> str:
        return f"Photo for lead {self.lead_id}"
