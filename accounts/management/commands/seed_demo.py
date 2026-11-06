"""Load a full fictional residential demo loop (idempotent)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from billing.models import Invoice, Payment
from billing.services import generate_invoice_for_job, record_payment
from followup.models import RecurringPlan, ReviewRequest
from followup.services import send_review_request_for_job, upsert_recurring_plan
from jobs.models import Job
from jobs.services import complete_job, schedule_job, set_weather_hold
from leads.models import Lead
from quoting.models import Quote
from quoting.services import (
    accept_quote,
    build_quote_from_lead,
    ensure_default_rate_card,
)

DEMO_OWNER_USERNAME = "jordan"
DEMO_OWNER_PASSWORD = "demo-pass-12345"
DEMO_OWNER_EMAIL = "jordan@lakesidepane.example"

# Stable keys for idempotent re-runs (fictional only).
MAIN_LEAD_EMAIL = "pat.homeowner@example.com"
EXTRA_NEW_EMAIL = "new.neighbor@example.com"
EXTRA_LOST_EMAIL = "lost.lead@example.com"


class Command(BaseCommand):
    help = (
        "Seed a full fictional Lakeside Pane Co. demo loop "
        "(owner, rate card, lead→quote→job→invoice→review→recurring). "
        "Safe to re-run."
    )

    def _log(self, msg, style=None):
        if self.verbosity < 1:
            return
        if style:
            self.stdout.write(style(msg))
        else:
            self.stdout.write(msg)

    @transaction.atomic
    def handle(self, *args, **options):
        self.verbosity = options.get("verbosity", 1)
        owner = self._ensure_owner()
        card = ensure_default_rate_card()
        self._log(f"Rate card ready: {card.name} (min ${card.minimum_charge})")

        main_lead = self._ensure_main_loop(card)
        self._ensure_extra_leads()

        self._log("Demo seed complete.", style=self.style.SUCCESS)
        self._log(
            f"  Owner login: {DEMO_OWNER_USERNAME} / {DEMO_OWNER_PASSWORD} "
            f"(user id={owner.pk})"
        )
        self._log(f"  Main lead: {main_lead.name} <{main_lead.email}>")

    def _ensure_owner(self):
        User = get_user_model()
        user, created = User.objects.get_or_create(
            username=DEMO_OWNER_USERNAME,
            defaults={
                "email": DEMO_OWNER_EMAIL,
                "first_name": "Jordan",
                "last_name": "Hale",
                "is_staff": True,
                "is_superuser": True,
            },
        )
        # Always reset the known demo password so README stays accurate.
        user.set_password(DEMO_OWNER_PASSWORD)
        user.email = DEMO_OWNER_EMAIL
        user.first_name = "Jordan"
        user.last_name = "Hale"
        user.is_staff = True
        user.is_superuser = True
        user.save()
        self._log(
            "Owner user created." if created else "Owner user already present (password refreshed)."
        )
        return user

    def _ensure_main_loop(self, card):
        exterior = card.items.get(code="exterior")
        screens = card.items.get(code="screens")

        lead, lead_created = Lead.objects.get_or_create(
            email=MAIN_LEAD_EMAIL,
            defaults={
                "name": "Pat Homeowner",
                "phone": "555-010-3001",
                "address_line1": "214 Lakeshore Dr",
                "city": "Cedar Falls",
                "zip_code": "50613",
                "service_interest": Lead.ServiceInterest.EXTERIOR,
                "stories": 2,
                "window_pane_estimate": 18,
                "how_heard": Lead.HeardAbout.GOOGLE,
                "message": "Exterior clean before the holidays — fictional demo lead.",
                "source": Lead.Source.WEB_FORM,
                "status": Lead.Status.NEW,
            },
        )
        if lead_created:
            self._log(f"Created main lead #{lead.pk}")

        quote = (
            Quote.objects.filter(lead=lead, customer_email=MAIN_LEAD_EMAIL)
            .order_by("id")
            .first()
        )
        if quote is None:
            quote = build_quote_from_lead(
                lead,
                [
                    {"item": exterior, "quantity": Decimal("18")},
                    {"item": screens, "quantity": Decimal("6")},
                ],
            )
            quote.notes = "Demo quote from seed_demo"
            quote.status = Quote.Status.SENT
            quote.sent_at = timezone.now() - timedelta(days=5)
            quote.save()
            self._log(f"Created quote #{quote.pk}")
        else:
            if quote.status == Quote.Status.DRAFT:
                quote.status = Quote.Status.SENT
                quote.sent_at = quote.sent_at or timezone.now()
                quote.save(update_fields=["status", "sent_at", "updated_at"])

        if quote.status != Quote.Status.ACCEPTED:
            accept_quote(quote)
            quote.refresh_from_db()
            self._log(f"Accepted quote #{quote.pk}")

        job = Job.objects.filter(quote=quote).first()
        if job is None:
            accept_quote(quote)  # ensure_job_for_quote on already-accepted path
            job = Job.objects.get(quote=quote)

        # Keep one completed job on the main loop.
        if job.status != Job.Status.COMPLETED:
            schedule_job(
                job,
                scheduled_date=date.today() - timedelta(days=10),
                time_window=Job.TimeWindow.MORNING,
            )
            complete_job(job)
            job.refresh_from_db()
            self._log(f"Completed job #{job.pk}")

        invoice = generate_invoice_for_job(job)
        if not invoice.payments.exists():
            record_payment(
                invoice,
                amount=invoice.total,
                method=Payment.Method.VENMO,
                note="Demo payment from seed_demo",
            )
            self._log(f"Recorded payment on invoice #{invoice.pk}")

        if not ReviewRequest.objects.filter(job=job).exists():
            send_review_request_for_job(job)
            self._log(f"Sent review ask for job #{job.pk}")

        plan = RecurringPlan.objects.filter(
            customer=job.customer,
            property=job.property,
            is_active=True,
        ).first()
        if plan is None:
            upsert_recurring_plan(
                customer=job.customer,
                property=job.property,
                frequency=RecurringPlan.Frequency.BIANNUAL,
                next_service_date=date.today() + timedelta(days=180),
                discount_percent=Decimal("15.00"),
                notes="Demo spring/fall plan from seed_demo",
            )
            self._log("Created biannual recurring plan")

        # Optional second job path for pipeline variety: weather-hold sibling lead/quote
        self._ensure_scheduled_weather_job(card)
        return lead

    def _ensure_scheduled_weather_job(self, card):
        """A second accepted quote still on the calendar (weather hold)."""
        email = "casey.scheduled@example.com"
        exterior = card.items.get(code="both")
        lead, _ = Lead.objects.get_or_create(
            email=email,
            defaults={
                "name": "Casey Scheduled",
                "phone": "555-010-3002",
                "address_line1": "88 River Rd",
                "city": "Waterloo",
                "zip_code": "50701",
                "service_interest": Lead.ServiceInterest.BOTH,
                "stories": 1,
                "window_pane_estimate": 12,
                "how_heard": Lead.HeardAbout.REFERRAL,
                "message": "Demo lead kept on the schedule / weather hold.",
                "source": Lead.Source.PHONE,
                "status": Lead.Status.CONTACTED,
            },
        )
        quote = Quote.objects.filter(lead=lead).order_by("id").first()
        if quote is None:
            quote = build_quote_from_lead(
                lead,
                [{"item": exterior, "quantity": Decimal("12")}],
            )
            quote.status = Quote.Status.SENT
            quote.sent_at = timezone.now() - timedelta(days=2)
            quote.save()
        if quote.status != Quote.Status.ACCEPTED:
            accept_quote(quote)
            quote.refresh_from_db()
        job = Job.objects.get(quote=quote)
        if job.status == Job.Status.UNSCHEDULED:
            schedule_job(
                job,
                scheduled_date=date.today() + timedelta(days=4),
                time_window=Job.TimeWindow.AFTERNOON,
            )
            set_weather_hold(job, note="Demo weather hold — high wind")
            self._log(f"Weather-hold job #{job.pk} ready")

    def _ensure_extra_leads(self):
        Lead.objects.get_or_create(
            email=EXTRA_NEW_EMAIL,
            defaults={
                "name": "Sam Newlead",
                "phone": "555-010-3003",
                "address_line1": "5 Maple Ct",
                "city": "Cedar Falls",
                "zip_code": "50613",
                "service_interest": Lead.ServiceInterest.INTERIOR,
                "stories": 2,
                "window_pane_estimate": 8,
                "how_heard": Lead.HeardAbout.NEXTDOOR,
                "message": "Just submitted — fictional new lead.",
                "source": Lead.Source.WEB_FORM,
                "status": Lead.Status.NEW,
            },
        )
        Lead.objects.get_or_create(
            email=EXTRA_LOST_EMAIL,
            defaults={
                "name": "Riley Lost",
                "phone": "555-010-3004",
                "address_line1": "910 Prairie St",
                "city": "Waterloo",
                "zip_code": "50703",
                "service_interest": Lead.ServiceInterest.EXTERIOR,
                "how_heard": Lead.HeardAbout.YARD_SIGN,
                "message": "Went with another cleaner — fictional lost lead.",
                "source": Lead.Source.PHONE,
                "status": Lead.Status.LOST,
                "lost_reason": "Chose another cleaner (demo)",
            },
        )
        self._log("Extra pipeline leads ensured (new + lost).")
