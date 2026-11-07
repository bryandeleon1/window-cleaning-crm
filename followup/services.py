"""Follow-up rules: ask for a review once a job is completed, and record a
recurring offer (schedule + optional discount). Offers never auto-bill.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from jobs.models import Job
from marketing.demo import GOOGLE_REVIEW_URL

from .emails import send_review_ask_email
from .models import RecurringPlan, ReviewRequest


@transaction.atomic
def send_review_request_for_job(job: Job) -> ReviewRequest:
    """Email the customer a review ask and store a ReviewRequest with snapshotted URL."""
    if job.status != Job.Status.COMPLETED:
        raise ValueError("Review asks are sent after a job is completed.")
    customer = job.customer
    to_email = (customer.email or "").strip()
    if not to_email:
        raise ValueError("Customer has no email address.")

    review_url = GOOGLE_REVIEW_URL
    send_review_ask_email(
        customer_name=customer.name,
        to_email=to_email,
        review_url=review_url,
    )
    return ReviewRequest.objects.create(
        job=job,
        customer=customer,
        google_review_url=review_url,
        recipient_email=to_email,
        sent_at=timezone.now(),
    )


def upsert_recurring_plan(
    *,
    customer,
    property,
    frequency: str,
    next_service_date,
    discount_percent=None,
    notes: str = "",
    plan: RecurringPlan | None = None,
) -> RecurringPlan:
    if plan is None:
        plan = RecurringPlan(customer=customer, property=property)
    else:
        if plan.customer_id != customer.pk or plan.property_id != property.pk:
            raise ValueError("Plan customer/property mismatch.")
    plan.frequency = frequency
    plan.next_service_date = next_service_date
    plan.discount_percent = discount_percent
    plan.notes = notes or ""
    plan.is_active = True
    plan.save()
    return plan
