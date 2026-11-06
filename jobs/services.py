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


TERMINAL = {Job.Status.COMPLETED, Job.Status.CANCELED}


def _lock(job: Job) -> None:
    fresh = Job.objects.select_for_update().get(pk=job.pk)
    for field in fresh._meta.concrete_fields:
        setattr(job, field.attname, getattr(fresh, field.attname))


def _lock_open(job: Job) -> None:
    _lock(job)
    if job.status in TERMINAL:
        raise ValueError(f"A {job.get_status_display().lower()} job cannot be changed.")


@transaction.atomic
def schedule_job(
    job: Job,
    *,
    scheduled_date: date,
    time_window: str = "",
    as_reschedule: bool = False,
    note: str = "",
) -> Job:
    """Schedule or reschedule a job (morning/afternoon window, no clock time)."""
    _lock_open(job)
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
    job.save()
    return job


@transaction.atomic
def set_weather_hold(job: Job, note: str = "") -> Job:
    _lock_open(job)
    job.status = Job.Status.WEATHER_HOLD
    job.status_note = note or job.status_note or "Weather hold"
    job.save(update_fields=["status", "status_note", "updated_at"])
    return job


@transaction.atomic
def complete_job(job: Job) -> Job:
    _lock(job)
    if job.status == Job.Status.COMPLETED:
        return job  # idempotent: keep original completed_at
    if job.status == Job.Status.CANCELED:
        raise ValueError("A canceled job cannot be completed.")
    job.status = Job.Status.COMPLETED
    job.completed_at = timezone.now()
    job.save(update_fields=["status", "completed_at", "updated_at"])
    return job
