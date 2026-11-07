"""Jobs are the booked work created when a quote is accepted, plus private job photos.
"""

from django.conf import settings
from django.db import models
from django.utils import timezone


class Job(models.Model):
    class Status(models.TextChoices):
        UNSCHEDULED = "unscheduled", "Unscheduled"
        SCHEDULED = "scheduled", "Scheduled"
        WEATHER_HOLD = "weather_hold", "Weather hold"
        RESCHEDULED = "rescheduled", "Rescheduled"
        COMPLETED = "completed", "Completed"
        CANCELED = "canceled", "Canceled"

    class TimeWindow(models.TextChoices):
        MORNING = "morning", "Morning"
        AFTERNOON = "afternoon", "Afternoon"
        UNSPECIFIED = "", "Not set"

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    quote = models.OneToOneField(
        "quoting.Quote",
        related_name="job",
        on_delete=models.CASCADE,
    )
    customer = models.ForeignKey(
        "clients.Customer",
        related_name="jobs",
        on_delete=models.PROTECT,
    )
    property = models.ForeignKey(
        "clients.Property",
        related_name="jobs",
        on_delete=models.PROTECT,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UNSCHEDULED,
        db_index=True,
    )
    scheduled_date = models.DateField(null=True, blank=True)
    time_window = models.CharField(
        max_length=20,
        choices=TimeWindow.choices,
        blank=True,
        default="",
    )
    status_note = models.CharField(max_length=255, blank=True)
    owner_notes = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Job #{self.pk} ({self.get_status_display()})"


def job_photo_upload_to(instance: "JobPhoto", filename: str) -> str:
    return f"jobs/{instance.job_id}/{filename}"


class JobPhoto(models.Model):
    """Private job photo. use_in_gallery is stored only — no auto-publish."""

    job = models.ForeignKey(Job, related_name="photos", on_delete=models.CASCADE)
    image = models.FileField(upload_to=job_photo_upload_to)
    caption = models.CharField(max_length=200, blank=True)
    use_in_gallery = models.BooleanField(
        default=False,
        help_text="Stored for a later gallery workflow; does not auto-publish.",
    )
    uploaded_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ["-uploaded_at"]

    def __str__(self) -> str:
        return f"Photo for job {self.job_id}"
