from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from clients.models import Customer, Property
from jobs.models import Job

from .forms import RecurringPlanForm
from .models import RecurringPlan, ReviewRequest
from .services import send_review_request_for_job, upsert_recurring_plan


@login_required
def followup_home(request):
    review_requests = ReviewRequest.objects.select_related("customer", "job")[:50]
    plans = RecurringPlan.objects.select_related("customer", "property").filter(is_active=True)
    return render(
        request,
        "followup/home.html",
        {"review_requests": review_requests, "plans": plans},
    )


@login_required
@require_POST
def send_review_ask(request, job_id):
    job = get_object_or_404(Job.objects.select_related("customer"), pk=job_id)
    try:
        rr = send_review_request_for_job(job)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("jobs:detail", pk=job.pk)
    messages.success(request, f"Review ask emailed to {rr.recipient_email}.")
    return redirect("jobs:detail", pk=job.pk)


@login_required
@require_http_methods(["GET", "POST"])
def recurring_plan_create(request, customer_id, property_id):
    customer = get_object_or_404(Customer, pk=customer_id)
    prop = get_object_or_404(Property, pk=property_id, customer=customer)
    if request.method == "POST":
        form = RecurringPlanForm(request.POST)
        if form.is_valid():
            plan = upsert_recurring_plan(
                customer=customer,
                property=prop,
                frequency=form.cleaned_data["frequency"],
                next_service_date=form.cleaned_data["next_service_date"],
                discount_percent=form.cleaned_data.get("discount_percent"),
                notes=form.cleaned_data.get("notes") or "",
            )
            messages.success(request, "Recurring offer saved.")
            return redirect("followup:plan_detail", pk=plan.pk)
    else:
        form = RecurringPlanForm()
    return render(
        request,
        "followup/plan_form.html",
        {"form": form, "customer": customer, "property": prop, "plan": None},
    )


@login_required
@require_http_methods(["GET", "POST"])
def recurring_plan_edit(request, pk):
    plan = get_object_or_404(
        RecurringPlan.objects.select_related("customer", "property"),
        pk=pk,
    )
    if request.method == "POST":
        form = RecurringPlanForm(request.POST, instance=plan)
        if form.is_valid():
            upsert_recurring_plan(
                customer=plan.customer,
                property=plan.property,
                frequency=form.cleaned_data["frequency"],
                next_service_date=form.cleaned_data["next_service_date"],
                discount_percent=form.cleaned_data.get("discount_percent"),
                notes=form.cleaned_data.get("notes") or "",
                plan=plan,
            )
            messages.success(request, "Recurring offer updated.")
            return redirect("followup:plan_detail", pk=plan.pk)
    else:
        form = RecurringPlanForm(instance=plan)
    return render(
        request,
        "followup/plan_form.html",
        {
            "form": form,
            "customer": plan.customer,
            "property": plan.property,
            "plan": plan,
        },
    )


@login_required
def recurring_plan_detail(request, pk):
    plan = get_object_or_404(
        RecurringPlan.objects.select_related("customer", "property"),
        pk=pk,
    )
    return render(request, "followup/plan_detail.html", {"plan": plan})
