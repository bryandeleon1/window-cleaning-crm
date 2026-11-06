"""Job helpers: create from accepted quote, schedule, weather hold, complete."""

from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from quoting.models import Quote

from .models import Job


@transaction.atomic
def ensure_job_for_quote(quote: Quote) -> Job | None:
    """Create a Job for an accepted quote if one does not exist yet."""
    if quote.status != Quote.Status.ACCEPTED:
        return Job.objects.filter(quote=quote).first()
    if not quote.customer_id or not quote.property_id:
        return None
    job, _created = Job.objects.get_or_create(
        quote=quote,
        defaults={
            "customer_id": quote.customer_id,
            "property_id": quote.property_id,
            "status": Job.Status.UNSCHEDULED,
        },
    )
    return job


def schedule_job(
    job: Job,
    *,
    scheduled_date: date,
    time_window: str = "",
    as_reschedule: bool = False,
    note: str = "",
) -> Job:
    """Schedule or reschedule a job (morning/afternoon window, no clock time)."""
    was_on_calendar = job.status in {
        Job.Status.SCHEDULED,
        Job.Status.WEATHER_HOLD,
        Job.Status.RESCHEDULED,
    }
    job.scheduled_date = scheduled_date
    job.time_window = time_window or ""
    if as_reschedule or was_on_calendar:
        job.status = Job.Status.RESCHEDULED
    else:
        job.status = Job.Status.SCHEDULED
    if note:
        job.status_note = note
    if job.status != Job.Status.COMPLETED:
        job.completed_at = None
    job.save()
    return job


def set_weather_hold(job: Job, note: str = "") -> Job:
    job.status = Job.Status.WEATHER_HOLD
    job.status_note = note or job.status_note or "Weather hold"
    job.save(update_fields=["status", "status_note", "updated_at"])
    return job


def complete_job(job: Job) -> Job:
    job.status = Job.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at", "updated_at"])
    return job
