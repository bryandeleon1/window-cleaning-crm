"""Owner notify + customer auto-reply for new leads (Django email)."""

from django.conf import settings
from django.core.mail import send_mail


def notify_owner_new_lead(lead) -> None:
    to = getattr(settings, "OWNER_NOTIFY_EMAIL", "") or ""
    if not to:
        return
    subject = f"New lead: {lead.name}"
    body = (
        f"New {lead.get_source_display().lower()} lead\n\n"
        f"Name: {lead.name}\n"
        f"Phone: {lead.phone or '—'}\n"
        f"Email: {lead.email or '—'}\n"
        f"City/ZIP: {lead.city or '—'} {lead.zip_code or ''}\n"
        f"Interest: {lead.get_service_interest_display()}\n\n"
        f"Message:\n{lead.message or '(none)'}\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [to],
        fail_silently=False,
    )


def auto_reply_customer(lead) -> None:
    if not lead.email:
        return
    subject = "We got your quote request — Lakeside Pane Co."
    body = (
        f"Hi {lead.name},\n\n"
        "Thanks for reaching out to Lakeside Pane Co. "
        "We received your request and will follow up soon "
        "(usually the same day during business hours).\n\n"
        "If it is urgent, call (555) 010-2040.\n\n"
        "— Jordan Hale\n"
        "Lakeside Pane Co. (demo brand)\n"
    )
    send_mail(
        subject,
        body,
        settings.DEFAULT_FROM_EMAIL,
        [lead.email],
        fail_silently=False,
    )


def send_new_lead_emails(lead) -> None:
    notify_owner_new_lead(lead)
    auto_reply_customer(lead)
