"""Job screens: the owner schedules, pauses for weather, completes, and adds private photos.

Views only handle forms, redirects, and messages; the status rules live in jobs/services.py.
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from notifications.files import private_image_response

from .forms import JobPhotoUploadForm, ScheduleJobForm, WeatherHoldForm
from .models import Job, JobPhoto
from .services import complete_job, schedule_job, set_weather_hold


@login_required
def job_list(request):
    jobs = Job.objects.select_related("customer", "property", "quote").all()
    status = request.GET.get("status")
    if status:
        jobs = jobs.filter(status=status)
    return render(
        request,
        "jobs/job_list.html",
        {"jobs": jobs, "statuses": Job.Status.choices, "current_status": status or ""},
    )


@login_required
def job_detail(request, pk):
    job = get_object_or_404(
        Job.objects.select_related("customer", "property", "quote").prefetch_related("photos"),
        pk=pk,
    )
    from billing.models import Invoice
    from followup.models import ReviewRequest

    invoice = Invoice.objects.filter(job=job).first()
    latest_review_request = (
        ReviewRequest.objects.filter(job=job).order_by("-sent_at").first()
    )
    return render(
        request,
        "jobs/job_detail.html",
        {
            "job": job,
            "invoice": invoice,
            "latest_review_request": latest_review_request,
            "schedule_form": ScheduleJobForm(
                initial={
                    "scheduled_date": job.scheduled_date,
                    "time_window": job.time_window,
                    "as_reschedule": job.status
                    in {
                        Job.Status.SCHEDULED,
                        Job.Status.WEATHER_HOLD,
                        Job.Status.RESCHEDULED,
                    },
                }
            ),
            "weather_form": WeatherHoldForm(),
            "photo_form": JobPhotoUploadForm(),
        },
    )


@login_required
@require_POST
def job_schedule(request, pk):
    """Put the job on the calendar (or move it); a completed/canceled job is refused."""
    job = get_object_or_404(Job, pk=pk)
    form = ScheduleJobForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Check the schedule date and try again.")
        return redirect("jobs:detail", pk=job.pk)
    try:
        schedule_job(
            job,
            scheduled_date=form.cleaned_data["scheduled_date"],
            time_window=form.cleaned_data.get("time_window") or "",
            as_reschedule=bool(form.cleaned_data.get("as_reschedule")),
            note=form.cleaned_data.get("note") or "",
        )
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("jobs:detail", pk=job.pk)
    messages.success(request, "Job schedule updated.")
    return redirect("jobs:detail", pk=job.pk)


@login_required
@require_POST
def job_weather_hold(request, pk):
    """Pause the job for weather; the owner reschedules once conditions clear."""
    job = get_object_or_404(Job, pk=pk)
    form = WeatherHoldForm(request.POST)
    note = form.cleaned_data.get("note") if form.is_valid() else "Weather hold"
    try:
        set_weather_hold(job, note=note or "Weather hold")
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("jobs:detail", pk=job.pk)
    messages.success(request, "Job placed on weather hold.")
    return redirect("jobs:detail", pk=job.pk)


@login_required
@require_POST
def job_complete(request, pk):
    """Mark the work done; this unlocks the invoice and the review ask."""
    job = get_object_or_404(Job, pk=pk)
    try:
        complete_job(job)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("jobs:detail", pk=job.pk)
    messages.success(request, "Job marked complete.")
    return redirect("jobs:detail", pk=job.pk)


@login_required
@require_http_methods(["POST"])
def job_photo_upload(request, pk):
    """Attach a private before/after photo (validated image, owner-only)."""
    job = get_object_or_404(Job, pk=pk)
    form = JobPhotoUploadForm(request.POST, request.FILES)
    if form.is_valid():
        photo = form.save(commit=False)
        photo.job = job
        photo.save()
        messages.success(request, "Photo uploaded (private).")
    else:
        messages.error(request, "Could not upload photo.")
    return redirect("jobs:detail", pk=job.pk)


@login_required
@require_GET
def job_photo(request, pk, photo_id):
    """Serve a job photo only to the logged-in owner (never via public /media/)."""
    photo = get_object_or_404(JobPhoto, pk=photo_id, job_id=pk)
    return private_image_response(photo.image)