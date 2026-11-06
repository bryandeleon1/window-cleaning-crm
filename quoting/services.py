"""Rate-card defaults and quote lifecycle helpers (accept also creates a Job)."""

from __future__ import annotations

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from clients.models import Customer, Property
from leads.models import Lead

from .models import Quote, QuoteLine, RateCard, RateCardItem

# Clearly fictional starter prices for the Lakeside Pane Co. demo.
STARTER_ITEMS = [
    # code, name, unit, price, is_addon, sort
    ("exterior", "Exterior window cleaning", RateCardItem.Unit.PER_WINDOW, "6.00", False, 10),
    ("interior", "Interior window cleaning", RateCardItem.Unit.PER_WINDOW, "6.00", False, 20),
    ("both", "Interior + exterior", RateCardItem.Unit.PER_WINDOW, "12.00", False, 30),
    ("screens", "Screens", RateCardItem.Unit.EACH, "3.50", True, 40),
    ("tracks-sills", "Tracks & sills", RateCardItem.Unit.PER_WINDOW, "4.00", True, 50),
    ("hard-water", "Hard-water treatment", RateCardItem.Unit.PER_WINDOW, "18.00", True, 60),
    ("skylights", "Skylights", RateCardItem.Unit.EACH, "25.00", True, 70),
    ("storm-windows", "Storm windows", RateCardItem.Unit.EACH, "15.00", True, 80),
    ("post-construction", "Post-construction clean", RateCardItem.Unit.PER_WINDOW, "16.00", True, 90),
]

DEFAULT_MINIMUM = Decimal("125.00")


def ensure_default_rate_card() -> RateCard:
    card, _ = RateCard.objects.get_or_create(
        name="Standard",
        defaults={"minimum_charge": DEFAULT_MINIMUM},
    )
    for code, name, unit, price, is_addon, sort in STARTER_ITEMS:
        RateCardItem.objects.get_or_create(
            rate_card=card,
            code=code,
            defaults={
                "name": name,
                "unit": unit,
                "unit_price": Decimal(price),
                "is_addon": is_addon,
                "is_active": True,
                "sort_order": sort,
            },
        )
    return card


def _lead_service_address(lead: Lead) -> str:
    parts = [p for p in [lead.address_line1, lead.city, lead.zip_code] if p]
    return ", ".join(parts)


@transaction.atomic
def build_quote_from_lead(lead: Lead, line_specs: list[dict]) -> Quote:
    """Create an itemized draft quote from rate-card line specs.

    Each spec: {item: RateCardItem, quantity: Decimal}
    """
    card = ensure_default_rate_card()
    quote = Quote.objects.create(
        lead=lead,
        status=Quote.Status.DRAFT,
        customer_name=lead.name,
        customer_email=lead.email,
        customer_phone=lead.phone,
        service_address=_lead_service_address(lead),
        minimum_charge=card.minimum_charge,
    )
    for idx, spec in enumerate(line_specs):
        item: RateCardItem = spec["item"]
        qty = Decimal(str(spec["quantity"]))
        if qty <= 0:
            continue
        line = QuoteLine(
            quote=quote,
            rate_card_item=item,
            description=item.name,
            unit=item.unit,
            quantity=qty,
            unit_price=item.unit_price,
            sort_order=idx,
        )
        line.recalculate_line_total()
        line.save()
    quote.recalculate_totals(save=True)
    if lead.status in {Lead.Status.NEW, Lead.Status.CONTACTED}:
        lead.status = Lead.Status.QUOTED
        lead.save(update_fields=["status", "updated_at"])
    return quote


@transaction.atomic
def accept_quote(quote: Quote) -> Quote:
    """Accept a quote: create Customer + one Property + Job, mark lead won.

    Idempotent for an accepted quote; refuses a lost quote.
    """
    _lock_fresh(quote)
    if quote.status == Quote.Status.LOST:
        raise ValueError("A lost quote cannot be accepted.")
    if quote.status == Quote.Status.ACCEPTED:
        from jobs.services import ensure_job_for_quote

        ensure_job_for_quote(quote)
        return quote

    lead = quote.lead
    name = quote.customer_name or (lead.name if lead else "Customer")
    email = quote.customer_email or (lead.email if lead else "")
    phone = quote.customer_phone or (lead.phone if lead else "")

    customer = Customer.objects.create(
        name=name,
        email=email,
        phone=phone,
    )

    address_line1 = ""
    city = ""
    zip_code = ""
    if lead:
        address_line1 = lead.address_line1 or "Address TBD"
        city = lead.city
        zip_code = lead.zip_code
    if quote.service_address and not lead:
        address_line1 = quote.service_address

    prop = Property.objects.create(
        customer=customer,
        address_line1=address_line1 or "Address TBD",
        city=city,
        zip_code=zip_code,
    )

    quote.customer = customer
    quote.property = prop
    quote.status = Quote.Status.ACCEPTED
    quote.accepted_at = timezone.now()
    quote.lost_reason = ""
    quote.save()

    if lead:
        lead.status = Lead.Status.WON
        lead.lost_reason = ""
        lead.save(update_fields=["status", "lost_reason", "updated_at"])

    from jobs.services import ensure_job_for_quote

    ensure_job_for_quote(quote)
    return quote


@transaction.atomic
def lose_quote(quote: Quote, reason: str) -> Quote:
    reason = (reason or "").strip()
    if not reason:
        raise ValueError("A lost reason is required.")
    _lock_fresh(quote)
    if quote.status == Quote.Status.ACCEPTED:
        raise ValueError("An accepted quote cannot be marked lost.")
    if quote.status == Quote.Status.LOST:
        raise ValueError("This quote is already lost.")
    quote.status = Quote.Status.LOST
    quote.lost_reason = reason
    quote.save(update_fields=["status", "lost_reason", "updated_at"])
    lead = quote.lead
    if lead and lead.status not in {Lead.Status.WON, Lead.Status.SPAM}:
        lead.status = Lead.Status.LOST
        lead.lost_reason = reason
        lead.save(update_fields=["status", "lost_reason", "updated_at"])
    return quote


def _lock_fresh(quote: Quote) -> None:
    """Reload the quote under a row lock so stale objects/double posts see current status."""
    fresh = Quote.objects.select_for_update().get(pk=quote.pk)
    for field in fresh._meta.concrete_fields:
        setattr(quote, field.attname, getattr(fresh, field.attname))


@transaction.atomic
def send_quote(quote: Quote) -> Quote:
    """Email the quote. Allowed from draft or sent (resend); refused once accepted or lost."""
    from .emails import send_quote_email

    _lock_fresh(quote)
    if quote.status == Quote.Status.ACCEPTED:
        raise ValueError("An accepted quote cannot be re-sent.")
    if quote.status == Quote.Status.LOST:
        raise ValueError("A lost quote cannot be sent.")
    send_quote_email(quote)
    quote.status = Quote.Status.SENT
    quote.sent_at = timezone.now()
    quote.save(update_fields=["status", "sent_at", "updated_at"])
    return quote
