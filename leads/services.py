"""Lead intake rules.

Every new customer starts as a *lead*: a request for a quote, never an
instant booking. Leads arrive three ways (public web form, a phone call the
owner logs, or a JSON webhook from a future live site). Whatever the channel,
the lead starts as NEW, the ZIP is normalized so service-area checks work,
and both the owner and the customer get an email so nothing slips through.
"""

from __future__ import annotations

from .emails import send_new_lead_emails
from .models import Lead, LeadPhoto
from .service_area import normalize_zip, zip_in_service_area


def _save_optional_photo(lead: Lead, uploaded) -> None:
    """Attach the customer's optional house photo (stored privately, owner-only)."""
    if not uploaded:
        return
    LeadPhoto.objects.create(lead=lead, image=uploaded)


def _optional_int(value):
    """Parse a loose number from outside data; blank or junk becomes 'unknown' (None)."""
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_how_heard(value: str) -> str:
    """Keep the marketing-source answer only if it is one of our known choices."""
    raw = (value or "").strip()
    valid = {c.value for c in Lead.HeardAbout}
    if raw in valid:
        return raw
    return ""


def _finish_new_lead(lead: Lead, source: str) -> Lead:
    """Stamp channel + NEW status, normalize ZIP, and save (shared by form channels)."""
    lead.source = source
    lead.status = Lead.Status.NEW
    lead.zip_code = normalize_zip(lead.zip_code)
    lead.save()
    return lead


def create_web_form_lead(lead: Lead, photo=None) -> Lead:
    """Save a quote request from the public website and notify owner + customer.

    `lead` is an unsaved Lead built from the validated public form.
    """
    _finish_new_lead(lead, Lead.Source.WEB_FORM)
    _save_optional_photo(lead, photo)
    send_new_lead_emails(lead)
    return lead


def create_phone_lead(lead: Lead) -> Lead:
    """Save a lead the owner took over the phone and send the usual emails."""
    _finish_new_lead(lead, Lead.Source.PHONE)
    send_new_lead_emails(lead)
    return lead


def create_lead_from_webhook_payload(payload: dict) -> tuple[Lead, bool | None]:
    """Create a NEW lead from a webhook JSON payload and email owner + customer.

    Accepts a few common field aliases (zip, address, window_count,
    pane_estimate, heard_about) so another site can post without exact names.
    Unknown service interests fall back to "unsure". Caller must ensure
    `name` is present. Returns (lead, zip_in_service_area or None if no ZIP).
    """
    name = (payload.get("name") or "").strip()

    interest = payload.get("service_interest") or Lead.ServiceInterest.UNSURE
    valid_interests = {c.value for c in Lead.ServiceInterest}
    if interest not in valid_interests:
        interest = Lead.ServiceInterest.UNSURE

    zip_code = normalize_zip(payload.get("zip_code") or payload.get("zip") or "")
    window_estimate = payload.get("window_pane_estimate")
    if window_estimate is None:
        window_estimate = payload.get("window_count") or payload.get("pane_estimate")

    lead = Lead.objects.create(
        name=name,
        email=(payload.get("email") or "").strip(),
        phone=(payload.get("phone") or "").strip(),
        address_line1=(payload.get("address_line1") or payload.get("address") or "").strip(),
        city=(payload.get("city") or "").strip(),
        zip_code=zip_code,
        service_interest=interest,
        stories=_optional_int(payload.get("stories")),
        window_pane_estimate=_optional_int(window_estimate),
        how_heard=_optional_how_heard(
            payload.get("how_heard") or payload.get("heard_about") or ""
        ),
        message=(payload.get("message") or "").strip(),
        source=Lead.Source.WEBHOOK,
        status=Lead.Status.NEW,
    )
    in_area = zip_in_service_area(zip_code) if zip_code else None
    send_new_lead_emails(lead)
    return lead, in_area
